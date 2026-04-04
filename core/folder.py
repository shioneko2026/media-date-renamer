"""
core/folder.py — Folder name parsing, building, and latest-date scanning.
Consolidates the duplicate parse_creator_folder() found across all 3 scripts.
"""

import os
import re
from datetime import datetime


# ── Folder name regex ─────────────────────────────────────────────────────────
# Matches: <anything> [YYYY-MM-DD] [Category] [Optional Status]
_FOLDER_RE = re.compile(
    r'^(.+?)\s+\[(\d{4}-\d{2}-\d{2})\]\s+\[([^\]]+)\](?:\s+\[([^\]]+)\])?$'
)


def parse_creator_folder(folder_name: str):
    """
    Parse a creator folder name.

    Expected formats:
        Creator [YYYY-MM-DD] [Category]
        Creator JP-Name [YYYY-MM-DD] [Category]
        Creator [YYYY-MM-DD] [Category] [Status]

    Returns (creator_full, date_str, category, status_or_None).
    creator_full is everything before the date bracket (may include JP name).
    Returns (None, None, None, None) on no match.
    """
    m = _FOLDER_RE.match(folder_name.strip())
    if not m:
        return None, None, None, None
    creator = m.group(1).strip()
    date_str = m.group(2).strip()
    category = m.group(3).strip()
    status = m.group(4).strip() if m.group(4) else None
    return creator, date_str, category, status


def build_folder_name(creator: str, date_str: str, category: str,
                      status, preset: dict) -> str:
    """
    Build a folder name from components using the preset's folder_template.

    Args:
        creator: Creator name (may include JP name as a single string)
        date_str: Date string e.g. '2024-06-01'
        category: Platform/source tag e.g. 'Fanbox'
        status: Optional status tag string or None
        preset: Active preset dict
    """
    from core.renamer import render_template

    folder_template = preset.get('folder_template', '{creator} [{date}] [{category}]')
    status_suffix = preset.get('folder_status_suffix', ' [{status}]')

    variables = {
        'creator': creator or '',
        'creator_jp': '',   # creator_full already includes JP if present
        'date': date_str or '',
        'category': category or '',
        'source': category or '',  # alias
    }

    name = render_template(folder_template, variables)

    if status:
        # Simple substitution — don't use render_template (it strips leading space)
        suffix = status_suffix.replace('{status}', status)
        name += suffix

    return name


def find_latest_date(folder_path: str, extensions: set):
    """
    Recursively scan all supported media files in folder_path.
    Returns (datetime_obj, 'YYYY-MM-DD', filename) of the latest date found,
    or (None, None, None) if nothing was found.

    Uses only video metadata (via pymediainfo) for latest-date scanning — not
    image EXIF — because this function is called before the full rename flow.
    Image EXIF scanning can be slow on large folders.
    """
    try:
        from pymediainfo import MediaInfo
    except ImportError:
        MediaInfo = None

    latest_dt = None
    latest_file = None

    for dirpath, _dirs, filenames in os.walk(folder_path):
        for fname in filenames:
            ext = os.path.splitext(fname)[1].lower()
            if ext not in extensions:
                continue
            filepath = os.path.join(dirpath, fname)
            dt = _get_video_datetime(filepath, MediaInfo)
            if dt is not None and (latest_dt is None or dt > latest_dt):
                latest_dt = dt
                latest_file = fname

    if latest_dt is not None:
        return latest_dt, latest_dt.strftime('%Y-%m-%d'), latest_file
    return None, None, None


def _get_video_datetime(filepath: str, MediaInfo):
    """Extract a datetime object from video metadata. Returns None on failure."""
    if MediaInfo is None:
        return None
    try:
        info = MediaInfo.parse(filepath, parse_speed=0.5)
        for track in info.tracks:
            for attr in ('encoded_date', 'tagged_date', 'recorded_date', 'mastered_date'):
                value = getattr(track, attr, None)
                if not value:
                    continue
                value = value.replace('UTC ', '').strip()
                for fmt in ('%Y-%m-%d %H:%M:%S', '%Y-%m-%dT%H:%M:%S', '%Y-%m-%d',
                            '%Y-%m-%dT%H:%M:%SZ', '%Y-%m-%d %H:%M:%SZ'):
                    try:
                        return datetime.strptime(value[:19], fmt[:len(value[:19])])
                    except ValueError:
                        continue
    except Exception:
        pass
    return None
