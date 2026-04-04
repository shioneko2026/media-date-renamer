"""
rename_media.py — Rename media files based on internal creation date metadata.
Triggered by right-clicking empty space INSIDE a creator folder.
Usage: pythonw.exe rename_media.py <folder_path>
"""

import sys
import os

# Ensure core/ and gui/ are importable from this script's directory
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PyQt6.QtWidgets import QApplication, QMessageBox

from core.config import load_config, get_active_preset
from core.folder import parse_creator_folder
from gui.fix_folder_dialog import FixFolderDialog
from gui.rename_window import RenameWindow


def show_error(title: str, message: str):
    app = QApplication.instance() or QApplication(sys.argv)
    QMessageBox.critical(None, title, message)


def main():
    if len(sys.argv) < 2:
        show_error('MediaRenamer Error',
                   'No folder path provided.\nUsage: rename_media.py <folder_path>')
        sys.exit(1)

    folder_path = sys.argv[1].strip().rstrip('\\/').rstrip('/')

    if not os.path.isdir(folder_path):
        show_error('MediaRenamer Error',
                   f'Path is not a valid directory:\n{folder_path}')
        sys.exit(1)

    config = load_config()
    preset = get_active_preset(config)

    folder_name = os.path.basename(folder_path)
    creator, _date, category, status = parse_creator_folder(folder_name)

    app = QApplication(sys.argv)
    app.setStyle('Fusion')

    if creator is None:
        dlg = FixFolderDialog(folder_name)
        if dlg.exec() != dlg.DialogCode.Accepted:
            sys.exit(0)
        creator, _date, category, _status = dlg.result_values()
        if creator is None:
            sys.exit(0)

    window = RenameWindow(folder_path, creator, category, preset)
    window.show()
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
