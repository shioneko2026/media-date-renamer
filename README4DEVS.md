> For the user-facing README, see [README.md](README.md).

# Media Date Renamer — Developer Reference

## Tech Stack & Dependencies

| Component | Library | Notes |
|---|---|---|
| GUI | PyQt6 | Settings panel, rename window, all dialogs |
| Video metadata | pymediainfo | Bundles `MediaInfo.dll` on Windows since v5.1 — no separate MediaInfo install required |
| Image metadata | Pillow | EXIF tags 36867 → 36868 → 306 (DateTimeOriginal → DateTimeDigitized → DateTime) |
| HEIC support | pillow-heif | Optional. Graceful fallback if not installed — HEIC files skipped, all else works |
| Registry / UAC | `winreg`, `ctypes` | stdlib only — no third-party Windows library needed |

Python 3.10+ required.

---

## Project Structure

```
Media Date Renamer/
├── app.py                    # PyQt6 settings panel (5-tab QMainWindow)
├── rename_media.py           # Thin launcher: context menu → rename workflow
├── update_folder_today.py    # Thin launcher: folder date → today
├── update_folder_latest.py   # Thin launcher: folder date → latest media date
├── install_helper.py         # Registry writer/remover with UAC elevation
├── config.json               # Auto-created; gitignored (contains local paths)
├── requirements.txt
├── core/
│   ├── config.py             # load/save config.json, preset helpers
│   ├── metadata.py           # Date extraction: video (pymediainfo) + image (Pillow/EXIF)
│   ├── renamer.py            # Build and apply rename plans
│   └── folder.py            # Parse/build folder names, find latest date
├── gui/
│   ├── rename_window.py      # QMainWindow: file list, scan thread, rename controls
│   ├── fix_folder_dialog.py  # QDialog: prompt for missing folder fields
│   └── confirm_dialog.py     # QDialog: confirm folder update operations
└── icons/                    # .ico files for context menu entries (empty by default)
```

---

## How to Run from Source

```bash
pip install -r requirements.txt

# Settings panel
python app.py

# Rename workflow (pass a folder path)
python rename_media.py "C:\path\to\creator folder"

# Register context menu (requires admin)
python install_helper.py --install --elevate
```

---

## Config Reference

`config.json` is auto-created on first run in the script directory. It is gitignored.

Key top-level fields:

| Field | Default | Description |
|---|---|---|
| `active_preset` | `"Universal Standard"` | Name of the currently selected preset |
| `presets` | array | List of preset objects (3 built-in, user presets appended) |
| `context_menu.items` | array | Ordered list of context menu entries |

### Preset fields

| Field | Description |
|---|---|
| `file_template` | Template string for file renaming. Variables: `{creator}`, `{creator_jp}`, `{date}`, `{post_title}`, `{original_name}`, `{category}` / `{source}` |
| `folder_template` | Template for folder renaming |
| `folder_status_suffix` | Appended to folder name when status is set (e.g. `" [{status}]"`) |
| `date_source_priority` | Order to try date sources: `["metadata", "filename", "null"]` |
| `include_subfolder_in_name` | If true, subfolder path is embedded into `original_name` using `subfolder_separator` |
| `skip_already_named` | If true, files already matching `Creator [YYYY-MM-DD]` pattern are skipped |
| `builtin` | If true, preset cannot be deleted from the UI |

### Template rendering (`core/renamer.py → render_template`)

- `{source}` and `{category}` are aliases — either works
- Blank optional variables collapse adjacent spaces (no double spaces)
- Orphaned ` - ` separator (when `{post_title}` is blank) is stripped via `(?<!\w) - `
- Creator prefix is auto-stripped from `original_stem` before rendering: `^Creator[\s\-_]+` (case-insensitive, falls back to original if stripping leaves nothing)

---

## Architecture Notes

### Context menu ordering

Windows sorts registry keys alphabetically. Keys are prefixed with zero-padded sort order: `01_renamemedia`, `02_updatefoldertoday`, `03_updatefolderlatest`. The visible label is stored separately in the key's `(Default)` value, independent of the key name.

Two registry hives are written:
- `HKCR\Directory\Background\shell\` — right-click inside a folder (`%V` = current dir)
- `HKCR\Directory\shell\` — right-click on a folder (`%1` = folder path)

### UAC elevation (`install_helper.py`)

Checks `ctypes.windll.shell32.IsUserAnAdmin()`. If not admin, re-launches self via `ShellExecuteW(None, "runas", ...)` and exits. The re-launched elevated process does the actual registry work.

### Rename scan thread

`gui/rename_window.py` runs the scan in a `QThread` with `pyqtSignal` to avoid blocking the UI. The plan is built in the worker and emitted back to the main thread via signal.

### Duplicate filename resolution

Deduplication is per `target_dir`. Each directory tracks `dir_names_used: set`. When a collision is detected (either with an existing file or another planned rename in the same directory), a `(1)`, `(2)`, ... suffix is appended to the stem before the extension.

### Plan item schema

Each entry in the rename plan carries:

```python
{
    'old_path': str,
    'new_path': str,
    'old_name': str,
    'new_name': str,
    'is_null': bool,
    'subfolder_parts': list,   # for in-place re-date rebuild
    'original_stem': str,      # for in-place re-date rebuild
    'ext': str,
    'target_dir': str,
}
```

`subfolder_parts`, `original_stem`, `ext`, and `target_dir` are stored so the rename window can rebuild `new_name` in-place when the user assigns a manual date — without re-scanning.

### Folder name parser regex

```
^(.+?)\s+\[(\d{4}-\d{2}-\d{2})\]\s+\[([^\]]+)\](?:\s+\[([^\]]+)\])?$
```

Groups: `creator`, `date`, `category`, optional `status`.

---

## Known Issues & Technical Debt

- **Subfolder dedup edge case**: files in nested subfolders that resolve to the same `new_name` within the same `target_dir` may still produce collisions in edge cases. The counter logic is correct but hasn't been exhaustively tested on deeply nested structures.
- **No post ID support**: intentionally excluded. Post IDs from raw filenames are indistinguishable from timestamps or sequence numbers and would produce false matches.
- **HEIC on first run**: `pillow-heif` must be installed before the app starts — the import is attempted at module load time. Restarting after install is required to activate HEIC support.
- **`config.json` migration**: `load_config()` deep-merges new default keys, but does not handle removed or renamed keys. Stale keys from older versions accumulate silently.

---

## Built-in Presets

Three presets ship with `builtin: true` (cannot be deleted from the UI):

| Preset | File template | Use case |
|---|---|---|
| Universal Standard | `{creator} {creator_jp} [{date}] {post_title} - {original_name} [{category}]` | FanFan gallery-dl convention |
| Video Only | Same as Universal Standard | Skips image extensions |
| Cleanup | `{creator} [{date}] {original_name} [{category}]` | Messy folders with no post metadata |
