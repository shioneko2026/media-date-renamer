"""
update_folder_today.py — Rename a creator folder using today's date.
Triggered by right-clicking ON a creator folder from outside.
Usage: pythonw.exe update_folder_today.py <folder_path>
"""

import sys
import os
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PyQt6.QtWidgets import QApplication, QMessageBox

from core.config import load_config, get_active_preset
from core.folder import parse_creator_folder, build_folder_name
from gui.fix_folder_dialog import FixFolderDialog
from gui.confirm_dialog import ConfirmFolderRenameDialog


def show_error(message: str):
    app = QApplication.instance() or QApplication(sys.argv)
    QMessageBox.critical(None, 'MediaRenamer Error', message)


def main():
    if len(sys.argv) < 2:
        show_error('No folder path provided.\nUsage: update_folder_today.py <folder_path>')
        sys.exit(1)

    folder_path = sys.argv[1].strip().rstrip('\\/').rstrip('/')

    if not os.path.isdir(folder_path):
        show_error(f'Path is not a valid directory:\n{folder_path}')
        sys.exit(1)

    folder_name = os.path.basename(folder_path)
    parent_dir = os.path.dirname(folder_path)
    today_str = date.today().strftime('%Y-%m-%d')

    config = load_config()
    preset = get_active_preset(config)

    creator, old_date, category, status = parse_creator_folder(folder_name)

    app = QApplication(sys.argv)
    app.setStyle('Fusion')

    if creator is None:
        dlg = FixFolderDialog(folder_name, date_str=today_str)
        if dlg.exec() != dlg.DialogCode.Accepted:
            sys.exit(0)
        creator, today_str, category, status = dlg.result_values()
        if creator is None:
            sys.exit(0)
        old_date = None
    else:
        dlg = ConfirmFolderRenameDialog(
            creator, today_str, category, status,
            date_label="today's date", preset=preset
        )
        if dlg.exec() != dlg.DialogCode.Accepted:
            sys.exit(0)
        today_str = dlg.confirmed_date() or today_str

    if old_date == today_str:
        sys.exit(0)

    new_name = build_folder_name(creator, today_str, category, status, preset)
    new_path = os.path.join(parent_dir, new_name)

    try:
        os.rename(folder_path, new_path)
    except Exception as e:
        QMessageBox.critical(None, 'MediaRenamer Error',
                             f'Failed to rename folder:\n{e}')
        sys.exit(1)


if __name__ == '__main__':
    main()
