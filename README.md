# Media Date Renamer

A Windows tool for batch-renaming media files and creator folders using embedded metadata dates. Integrates into the Windows right-click context menu and includes a GUI settings panel with a preset system.

> **Work in progress.** Core renaming and folder update features are functional. Some features are still being developed.

---

## What It Does

- Renames media files using their embedded creation date (from metadata or EXIF)
- Supports video files (via MediaInfo) and images (via EXIF — jpg, png, webp, heic, bmp, tiff)
- Automatically strips creator name prefix from filenames to prevent double naming
- Updates creator folder dates to today or to the latest date found in the folder's media
- Integrates into the Windows right-click context menu (on folders and inside folders)
- Comes with a GUI settings panel (`open_settings.bat`) for configuring presets, context menu entries, and supported file types

### Naming Convention

The default **Universal Standard** preset follows the FanFan gallery-dl convention:

```
# File
Creator CreatorJP [YYYY-MM-DD] Post Title - OriginalFilename [Source].ext

# Folder
Creator CreatorJP [YYYY-MM-DD] [Source]
Creator CreatorJP [YYYY-MM-DD] [Source] [Status]
```

Optional fields (`CreatorJP`, `Post Title`) collapse cleanly when blank — no double spaces or orphaned dashes.

---

## Screenshots

**Settings panel — Rename tab**

![Settings panel Rename tab](docs/screenshots/01_settings_rename_tab.jpg)

**When a folder name doesn't match the expected format, a Fix Folder dialog appears. Date is auto-detected from the files inside when available.**

<table>
<tr>
<td><img src="docs/screenshots/02_fix_folder_dialog.jpg" alt="Fix Folder dialog" width="500"/></td>
<td><img src="docs/screenshots/03_fix_folder_autodate.jpg" alt="Fix Folder with auto-detected date" width="460"/></td>
</tr>
</table>

**Rename preview window — review every planned rename before confirming**

![Rename preview window](docs/screenshots/04_rename_preview.jpg)

**Before and after — Explorer view of renamed files and folder**

<table>
<tr>
<td><img src="docs/screenshots/05_renamed_files.jpg" alt="Renamed files in Explorer" width="800"/></td>
</tr>
<tr>
<td><img src="docs/screenshots/06_renamed_folder.jpg" alt="Renamed folder result" width="460"/></td>
</tr>
</table>

---

## Requirements

- Windows 10/11
- Python 3.10+
- MediaInfo (for video metadata)

---

## Setup

### 1. Install Python

Download from [python.org](https://www.python.org/downloads/). During install, **check "Add Python to PATH"**.

### 2. Install MediaInfo

Download the GUI version from [mediaarea.net](https://mediaarea.net/en/MediaInfo/Download/Windows). pymediainfo requires the underlying MediaInfo DLL that comes with this installer.

### 3. Install Python dependencies

Double-click `install_dependencies.bat`, or run:

```
pip install -r requirements.txt
```

### 4. Register the right-click menu

Right-click `install.bat` → **Run as administrator**.

This registers the context menu entries in the Windows registry. If you ever move the folder, re-run this.

---

## Usage

### Context menu (right-click)

Right-click **inside** a media folder (on empty space) or **on** a creator folder:

| Option | What it does |
|---|---|
| Rename Media Files | Scans the folder, shows a rename preview, lets you confirm |
| Update Folder Date (Today) | Renames the folder using today's date |
| Update Folder Date (Latest) | Scans media files, renames the folder using the most recent date found |

If no files need renaming, a "Nothing to Rename!" prompt is shown instead of failing silently.

#### Rename window controls

| Button | What it does |
|---|---|
| Deselect Null | Deselects files shown in orange (no readable media creation date) |
| What's Null? | Explains how dates are determined and what null means |
| Manual Re-date | Assigns a custom YYYY-MM-DD date to all selected files |

Files with no embedded date are highlighted in orange. You can leave them checked and rename with `[null]` in the filename, deselect them to skip, or use Manual Re-date to assign a date yourself.

### Settings GUI

Double-click `open_settings.bat` to open the settings panel. From here you can:

- Create, duplicate, and switch between naming presets
- Configure which file types are included
- Customize context menu labels and order
- Browse to a folder and run any operation directly (Rename tab)

---

## Folder Name Format

MediaRenamer expects creator folders in this format:

```
Creator [YYYY-MM-DD] [Source]
Creator [YYYY-MM-DD] [Source] [Status]
```

Status options:

| Status | Meaning |
|---|---|
| Obtained | Everything obtained up to the latest date. Nothing missing except intentional deletions. |
| Partial | Missing some content that wasn't intentionally deleted. |
| Uncertain | Collection state unknown. |

If a folder doesn't match the expected format, the tool will prompt you to fill in the missing details before proceeding.

---

## Uninstalling

Right-click `uninstall.bat` → **Run as administrator**.

Removes only the registry entries. Python, MediaInfo, and your files are untouched.

---

## Troubleshooting

**Nothing happens on right-click** — Re-run `install.bat` as administrator. If you moved the folder, run it again to update paths.

**"Python is not recognized"** — Reinstall Python and tick "Add Python to PATH". Restart any open terminals.

**All dates show as null** — The file has no embedded date. Check if the filename contains a date; otherwise it will stay as-is until you set one manually.

**"Failed to rename folder"** — A file inside the folder is open in another program. Close it and retry.
