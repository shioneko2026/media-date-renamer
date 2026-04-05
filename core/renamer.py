"""
core/renamer.py — Build and apply file rename plans using preset templates.
"""

import os
import re


def render_template(template: str, variables: dict) -> str:
    """
    Render a template string substituting {variable} placeholders.

    Rules:
    - Known variables with empty string values collapse their preceding space(s).
      e.g. "{creator} {creator_jp} [{date}]" with creator_jp='' → "Creator [Date]"
    - After substitution, any run of 2+ spaces is collapsed to one space.
    - Leading/trailing whitespace is stripped.
    - {source} is an alias for {category}.
    """
    # Normalize alias
    if 'category' in variables and 'source' not in variables:
        variables = dict(variables, source=variables['category'])
    if 'source' in variables and 'category' not in variables:
        variables = dict(variables, category=variables['source'])

    def replacer(m):
        key = m.group(1)
        val = variables.get(key, '')
        return str(val) if val is not None else ''

    result = re.sub(r'\{(\w+)\}', replacer, template)
    # Collapse multiple spaces (handles blank optional variables)
    result = re.sub(r' {2,}', ' ', result)
    # Remove orphaned " - " separators when the preceding field was blank
    # e.g. "{post_title} - {original_name}" with blank post_title → "- filename" → "filename"
    result = re.sub(r'(?<!\w) - ', ' ', result)
    return result.strip()


def collect_media_files(creator_folder: str, extensions: set) -> list:
    """
    Recursively collect all files with matching extensions under creator_folder.
    Returns list of (abs_path, subfolder_parts) tuples, where subfolder_parts
    is a list of folder names relative to creator_folder (empty for root-level files).
    """
    files = []
    for dirpath, _dirs, filenames in os.walk(creator_folder):
        rel = os.path.relpath(dirpath, creator_folder)
        subfolder_parts = [] if rel == '.' else rel.split(os.sep)
        for fname in filenames:
            ext = os.path.splitext(fname)[1].lower()
            if ext in extensions:
                files.append((os.path.join(dirpath, fname), subfolder_parts))
    return files


def build_new_name(creator: str, creator_jp: str, date_str: str,
                   post_title: str, subfolder_parts: list, original_stem: str,
                   category: str, ext: str, preset: dict) -> str:
    """
    Build the desired new filename (including extension) using the preset's file_template.
    Handles subfolder embedding when include_subfolder_in_name is True.
    """
    separator = preset.get('subfolder_separator', ' - ')
    include_sub = preset.get('include_subfolder_in_name', True)

    # Strip creator name prefix from original_stem to prevent double naming.
    # Matches "Creator- ", "Creator_ ", "Creator " etc. at the start (case-insensitive).
    clean_stem = original_stem
    if creator:
        clean_stem = re.sub(
            r'^' + re.escape(creator.strip()) + r'[\s\-_]+',
            '',
            original_stem,
            flags=re.IGNORECASE
        ).strip()
        # Fall back to original if stripping left nothing
        if not clean_stem:
            clean_stem = original_stem

    if include_sub and subfolder_parts:
        effective_name = separator.join(subfolder_parts) + separator + clean_stem
    else:
        effective_name = clean_stem

    file_template = preset.get(
        'file_template',
        '{creator} [{date}] {original_name} [{category}]'
    )

    variables = {
        'creator': creator or '',
        'creator_jp': creator_jp or '',
        'date': date_str or '',
        'post_title': post_title or '',
        'original_name': effective_name or '',
        'category': category or '',
        'source': category or '',
    }

    stem = render_template(file_template, variables)
    return stem + ext


def is_already_correctly_named(fname: str, creator: str, preset: dict) -> bool:
    """
    Check whether a filename already matches the expected pattern for this creator/preset.
    Uses a simple heuristic: does the name start with Creator [YYYY-MM-DD]?
    """
    if not creator:
        return False
    pattern = r'^' + re.escape(creator.strip()) + r'\s+\[\d{4}-\d{2}-\d{2}\]'
    return bool(re.match(pattern, fname, re.IGNORECASE))


def build_rename_plan(creator_folder: str, creator: str, creator_jp: str,
                      post_title: str, category: str, preset: dict) -> list:
    """
    Build a rename plan for all media files in creator_folder.

    Returns a list of dicts:
        {
            'old_path': str,
            'new_path': str,
            'old_name': str,
            'new_name': str,
            'is_null': bool,   # True if no date could be extracted
        }

    Files already correctly named (per is_already_correctly_named) are skipped
    when preset['skip_already_named'] is True.
    """
    from core.metadata import get_file_date, extract_date_from_filename
    from core.config import get_all_extensions

    extensions = get_all_extensions(preset)
    priority = preset.get('date_source_priority', ['metadata', 'filename', 'null'])
    skip = preset.get('skip_already_named', True)

    files = collect_media_files(creator_folder, extensions)
    plan = []
    dir_names_used: dict = {}

    for abs_path, subfolder_parts in files:
        fname = os.path.basename(abs_path)
        ext = os.path.splitext(fname)[1]
        original_stem = os.path.splitext(fname)[0]
        target_dir = os.path.dirname(abs_path)

        if skip and is_already_correctly_named(fname, creator, preset):
            continue

        # Try to get date from metadata, then filename, then null
        date_str, _source = get_file_date(abs_path, priority)

        # Additional fallback: check if the filename already has a bracketed date
        if date_str is None:
            date_str = extract_date_from_filename(fname)

        is_null = date_str is None
        display_date = date_str if date_str else 'null'

        desired_name = build_new_name(
            creator, creator_jp, display_date, post_title,
            subfolder_parts, original_stem, category, ext, preset
        )

        if target_dir not in dir_names_used:
            dir_names_used[target_dir] = set()

        # Resolve duplicates
        stem_part = desired_name[: -len(ext)] if ext else desired_name
        candidate = desired_name
        counter = 1
        while (
            (os.path.exists(os.path.join(target_dir, candidate))
             and os.path.join(target_dir, candidate) != abs_path)
            or candidate in dir_names_used[target_dir]
        ):
            candidate = f'{stem_part} ({counter}){ext}'
            counter += 1

        dir_names_used[target_dir].add(candidate)
        plan.append({
            'old_path': abs_path,
            'new_path': os.path.join(target_dir, candidate),
            'old_name': fname,
            'new_name': candidate,
            'is_null': is_null,
            # Stored so the rename window can rebuild new_name after a manual re-date
            'subfolder_parts': subfolder_parts,
            'original_stem': original_stem,
            'ext': ext,
            'target_dir': target_dir,
        })

    return plan


def apply_rename_plan(plan: list, selected_indices: list) -> tuple:
    """
    Apply the rename plan for the given selected indices.
    Returns (renamed_count, error_messages_list).
    """
    errors = []
    renamed = 0
    for i in selected_indices:
        if i >= len(plan):
            continue
        item = plan[i]
        try:
            os.rename(item['old_path'], item['new_path'])
            renamed += 1
        except Exception as e:
            errors.append(f"{item['old_name']}: {e}")
    return renamed, errors
