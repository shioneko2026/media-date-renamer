"""
core/config.py — Load and save config.json. Provides DEFAULT_CONFIG and helpers.
"""

import json
import os

_SCRIPT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_PATH = os.path.join(_SCRIPT_DIR, 'config.json')

DEFAULT_CONFIG = {
    "version": 1,
    "active_preset": "Universal Standard",
    "presets": [
        {
            "name": "Universal Standard",
            "builtin": True,
            "description": "Full FanFan gallery-dl convention with optional JP name and post title.",
            "file_template": "{creator} {creator_jp} [{date}] {post_title} - {original_name} [{category}]",
            "folder_template": "{creator} {creator_jp} [{date}] [{category}]",
            "folder_status_suffix": " [{status}]",
            "date_format": "%Y-%m-%d",
            "date_source_priority": ["metadata", "filename", "null"],
            "subfolder_separator": " - ",
            "include_subfolder_in_name": True,
            "skip_already_named": True,
            "supported_extensions": {
                "video": [".mp4", ".mov", ".mkv", ".avi", ".wmv", ".flv", ".webm", ".m4v"],
                "image": [".jpg", ".jpeg", ".png", ".webp", ".heic", ".bmp", ".tiff"],
                "other": [".gif"]
            }
        },
        {
            "name": "Video Only",
            "builtin": True,
            "description": "Like Universal Standard but skips image files.",
            "file_template": "{creator} {creator_jp} [{date}] {post_title} - {original_name} [{category}]",
            "folder_template": "{creator} {creator_jp} [{date}] [{category}]",
            "folder_status_suffix": " [{status}]",
            "date_format": "%Y-%m-%d",
            "date_source_priority": ["metadata", "filename", "null"],
            "subfolder_separator": " - ",
            "include_subfolder_in_name": True,
            "skip_already_named": True,
            "supported_extensions": {
                "video": [".mp4", ".mov", ".mkv", ".avi", ".wmv", ".flv", ".webm", ".m4v"],
                "image": [],
                "other": [".gif"]
            }
        },
        {
            "name": "Cleanup",
            "builtin": True,
            "description": "For messy folders with no post metadata. Minimal: Creator [Date] Filename [Category].",
            "file_template": "{creator} [{date}] {original_name} [{category}]",
            "folder_template": "{creator} [{date}] [{category}]",
            "folder_status_suffix": " [{status}]",
            "date_format": "%Y-%m-%d",
            "date_source_priority": ["metadata", "filename", "null"],
            "subfolder_separator": " - ",
            "include_subfolder_in_name": True,
            "skip_already_named": False,
            "supported_extensions": {
                "video": [".mp4", ".mov", ".mkv", ".avi", ".wmv", ".flv", ".webm", ".m4v"],
                "image": [".jpg", ".jpeg", ".png", ".webp", ".heic", ".bmp", ".tiff"],
                "other": [".gif"]
            }
        }
    ],
    "context_menu": {
        "items": [
            {
                "id": "rename_media",
                "label": "Rename Media Files",
                "icon": "icons\\rename_media.ico",
                "enabled": True,
                "trigger": "background",
                "script": "rename_media.py",
                "position": "top",
                "sort_order": 1
            },
            {
                "id": "update_folder_today",
                "label": "Update Folder Date (Today)",
                "icon": "icons\\folder_today.ico",
                "enabled": True,
                "trigger": "directory",
                "script": "update_folder_today.py",
                "position": "bottom",
                "sort_order": 2
            },
            {
                "id": "update_folder_latest",
                "label": "Update Folder Date (Latest Media Date)",
                "icon": "icons\\folder_latest.ico",
                "enabled": True,
                "trigger": "directory",
                "script": "update_folder_latest.py",
                "position": "bottom",
                "sort_order": 3
            }
        ]
    },
    "ui": {
        "confirm_before_rename": True,
        "show_skipped_files": False,
        "warn_on_null_dates": True
    }
}


def _deep_merge(base: dict, override: dict) -> dict:
    """Merge override into base, preserving base keys not present in override."""
    result = dict(base)
    for k, v in override.items():
        if k in result and isinstance(result[k], dict) and isinstance(v, dict):
            result[k] = _deep_merge(result[k], v)
        else:
            result[k] = v
    return result


def load_config() -> dict:
    """
    Load config.json. If missing or unreadable, write and return DEFAULT_CONFIG.
    Deep-merges with DEFAULT_CONFIG so new keys always have defaults.
    """
    if os.path.isfile(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
                loaded = json.load(f)
            return _deep_merge(DEFAULT_CONFIG, loaded)
        except Exception:
            pass
    # Create the file with defaults
    save_config(DEFAULT_CONFIG)
    return dict(DEFAULT_CONFIG)


def save_config(config: dict) -> None:
    """Serialize config to config.json."""
    with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=2, ensure_ascii=False)


def get_active_preset(config: dict) -> dict:
    """Return the preset dict matching config['active_preset']; falls back to first preset."""
    name = config.get('active_preset', '')
    for p in config.get('presets', []):
        if p.get('name') == name:
            return p
    presets = config.get('presets', [])
    return presets[0] if presets else DEFAULT_CONFIG['presets'][0]


def get_all_extensions(preset: dict) -> set:
    """Flatten video + image + other extension lists into a lowercase set."""
    exts = preset.get('supported_extensions', {})
    result = set()
    for bucket in ('video', 'image', 'other'):
        for e in exts.get(bucket, []):
            result.add(e.lower())
    return result
