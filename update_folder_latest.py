"""
update_folder_latest.py — Rename a creator folder using the latest media creation date found inside.
Triggered by right-clicking ON a creator folder from outside.
Usage: pythonw.exe update_folder_latest.py <folder_path>
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PyQt6.QtWidgets import QApplication, QMessageBox

from core.config import load_config, get_active_preset, get_all_extensions
from core.folder import parse_creator_folder, build_folder_name, find_latest_date
from gui.fix_folder_dialog import FixFolderDialog
from gui.confirm_dialog import ConfirmFolderRenameDialog


def show_error(message: str):
    app = QApplication.instance() or QApplication(sys.argv)
    QMessageBox.critical(None, 'MediaRenamer Error', message)


def main():
    if len(sys.argv) < 2:
        show_error('No folder path provided.\nUsage: update_folder_latest.py <folder_path>')
        sys.exit(1)

    folder_path = sys.argv[1].strip().rstrip('\\/').rstrip('/')

    if not os.path.isdir(folder_path):
        show_error(f'Path is not a valid directory:\n{folder_path}')
        sys.exit(1)

    folder_name = os.path.basename(folder_path)
    parent_dir = os.path.dirname(folder_path)

    config = load_config()
    preset = get_active_preset(config)
    extensions = get_all_extensions(preset)

    # Scan for latest date before showing any UI
    try:
        _dt, latest_date_str, latest_file = find_latest_date(folder_path, extensions)
    except Exception as e:
        show_error(f'Error scanning folder for media dates:\n{e}')
        sys.exit(1)

    if latest_date_str is None:
        show_error('No readable media creation date found in this folder.')
        sys.exit(1)

    creator, old_date, category, status = parse_creator_folder(folder_name)

    app = QApplication(sys.argv)
    app.setStyle('Fusion')

    if creator is None:
        dlg = FixFolderDialog(folder_name, date_str=latest_date_str,
                              latest_file=latest_file or '')
        if dlg.exec() != dlg.DialogCode.Accepted:
            sys.exit(0)
        creator, latest_date_str, category, status = dlg.result_values()
        if creator is None:
            sys.exit(0)
        old_date = None
    else:
        dlg = ConfirmFolderRenameDialog(
            creator, latest_date_str, category, status,
            date_label='latest media date',
            latest_file=latest_file or '',
            preset=preset
        )
        if dlg.exec() != dlg.DialogCode.Accepted:
            sys.exit(0)
        latest_date_str = dlg.confirmed_date() or latest_date_str

    if old_date == latest_date_str:
        sys.exit(0)

    new_name = build_folder_name(creator, latest_date_str, category, status, preset)
    new_path = os.path.join(parent_dir, new_name)

    try:
        os.rename(folder_path, new_path)
    except Exception as e:
        QMessageBox.critical(None, 'MediaRenamer Error',
                             f'Failed to rename folder:\n{e}')
        sys.exit(1)


if __name__ == '__main__':
    main()
