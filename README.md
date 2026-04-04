# Media Date Renamer

A Windows tool for batch-renaming media files and creator folders using embedded metadata dates. Integrates into the Windows right-click context menu and includes a GUI settings panel with a preset system.

> **Work in progress.** Core renaming and folder update features are functional. Some features are still being developed.

---

## What It Does

- Renames media files using their embedded creation date (from metadata or EXIF)
- Supports video files (via MediaInfo) and images (via EXIF — jpg, png, webp, heic, bmp, tiff)
- Updates creator folder dates to today or to the latest date found in the folder's media
- Integrates into the Windows right-click context menu (on folders and inside folders)
- Comes with a GUI settings panel (`open_settings.bat`) for configuring presets, context menu entries, and supported file types

### Naming Convention

The default **Universal Standard** preset follows the FanFan gallery-dl convention:

```
# File
Creator CreatorJP [YYYY-MM-DD] Post Title - OriginalFilename [Category].ext

# Folder
Creator CreatorJP [YYYY-MM-DD] [Category]
Creator CreatorJP [YYYY-MM-DD] [Category] [Status]
```

Optional fields (`CreatorJP`, `Post Title`) collapse cleanly when blank — no double spaces or orphaned dashes.

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
Creator [YYYY-MM-DD] [Category]
Creator [YYYY-MM-DD] [Category] [Status]
```

If a folder doesn't match, the tool will prompt you to fill in the missing details.

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
