"""
app.py — MediaRenamer Settings Panel.
Launch directly: pythonw.exe app.py
Or add as a context menu item pointing to this script.
"""

import sys
import os
import copy
import subprocess

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QTabWidget,
    QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QTextEdit,
    QPushButton, QComboBox, QCheckBox, QListWidget, QListWidgetItem,
    QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView,
    QFileDialog, QMessageBox, QGroupBox, QScrollArea, QFrame,
    QSizePolicy, QGridLayout, QSplitter
)
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QFont, QColor

from core.config import load_config, save_config, DEFAULT_CONFIG, get_active_preset


# ── Main window ───────────────────────────────────────────────────────────────

class SettingsWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self._config = load_config()
        self._dirty = False

        self.setWindowTitle('MediaRenamer Settings')
        self.setMinimumSize(820, 600)
        self.resize(900, 660)

        self._build_ui()
        self._load_all_tabs()

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self._tabs = QTabWidget()
        layout.addWidget(self._tabs, 1)

        # Create tabs
        self._preset_tab = _PresetsTab(self._config, self._on_dirty)
        self._rename_tab = _RenameTab(self._config)
        self._menu_tab = _ContextMenuTab(self._config, self._on_dirty)
        self._filetypes_tab = _FileTypesTab(self._config, self._on_dirty)
        self._about_tab = _AboutTab()

        self._tabs.addTab(self._preset_tab, 'Presets')
        self._tabs.addTab(self._rename_tab, 'Rename')
        self._tabs.addTab(self._menu_tab, 'Context Menu')
        self._tabs.addTab(self._filetypes_tab, 'File Types')
        self._tabs.addTab(self._about_tab, 'About')

        # Bottom button bar
        btn_bar = QWidget()
        btn_bar.setFixedHeight(48)
        btn_bar.setStyleSheet('background: #f5f5f5; border-top: 1px solid #ddd;')
        btn_layout = QHBoxLayout(btn_bar)
        btn_layout.setContentsMargins(12, 6, 12, 6)

        self._save_btn = QPushButton('Save && Close')
        self._save_btn.setFixedWidth(130)
        self._save_btn.setStyleSheet(
            'background-color: #1976D2; color: white; font-weight: bold; padding: 4px 8px;'
        )
        self._save_btn.clicked.connect(self._on_save)
        cancel_btn = QPushButton('Cancel')
        cancel_btn.setFixedWidth(100)
        cancel_btn.clicked.connect(self.close)

        self._status_lbl = QLabel('')
        self._status_lbl.setStyleSheet('color: #666; font-size: 8pt;')

        btn_layout.addWidget(self._status_lbl)
        btn_layout.addStretch()
        btn_layout.addWidget(cancel_btn)
        btn_layout.addWidget(self._save_btn)

        layout.addWidget(btn_bar)

    def _load_all_tabs(self):
        self._preset_tab.load(self._config)
        self._menu_tab.load(self._config)
        self._filetypes_tab.load(self._config)

    def _on_dirty(self):
        self._dirty = True
        self._status_lbl.setText('Unsaved changes')

    def _on_save(self):
        # Collect from each tab
        self._preset_tab.save_to(self._config)
        self._menu_tab.save_to(self._config)
        self._filetypes_tab.save_to(self._config)

        save_config(self._config)
        self._status_lbl.setText('Saved.')
        self._dirty = False
        self.close()


# ── Rename Tab ────────────────────────────────────────────────────────────────

class _RenameTab(QWidget):
    """
    Direct rename/folder-update operations without needing the context menu.
    Pick a folder, then run any of the three operations using the active preset.
    """

    def __init__(self, config: dict):
        super().__init__()
        self._config = config
        self._rename_win = None   # keep reference so window isn't GC'd
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 12)
        layout.setSpacing(10)

        # ── Folder picker ─────────────────────────────────────────────────────
        layout.addWidget(_bold('Folder'))
        folder_row = QHBoxLayout()
        self._folder_edit = QLineEdit()
        self._folder_edit.setPlaceholderText('Select or paste a creator folder path…')
        self._folder_edit.textChanged.connect(self._on_folder_changed)
        browse_btn = QPushButton('Browse…')
        browse_btn.setFixedWidth(80)
        browse_btn.clicked.connect(self._browse_folder)
        folder_row.addWidget(self._folder_edit)
        folder_row.addWidget(browse_btn)
        layout.addLayout(folder_row)

        # ── Detected info panel ───────────────────────────────────────────────
        self._info_frame = QFrame()
        self._info_frame.setFrameShape(QFrame.Shape.StyledPanel)
        self._info_frame.setStyleSheet('background: #f9f9f9; border: 1px solid #ddd; border-radius: 4px;')
        info_layout = QGridLayout(self._info_frame)
        info_layout.setContentsMargins(10, 8, 10, 8)
        info_layout.setSpacing(4)

        info_layout.addWidget(_grey('Creator:'), 0, 0)
        self._lbl_creator = QLabel('—')
        self._lbl_creator.setFont(QFont('Consolas', 9))
        info_layout.addWidget(self._lbl_creator, 0, 1)

        info_layout.addWidget(_grey('Category:'), 1, 0)
        self._lbl_category = QLabel('—')
        self._lbl_category.setFont(QFont('Consolas', 9))
        info_layout.addWidget(self._lbl_category, 1, 1)

        info_layout.addWidget(_grey('Date:'), 2, 0)
        self._lbl_date = QLabel('—')
        self._lbl_date.setFont(QFont('Consolas', 9))
        info_layout.addWidget(self._lbl_date, 2, 1)

        info_layout.addWidget(_grey('Status:'), 3, 0)
        self._lbl_status = QLabel('—')
        self._lbl_status.setFont(QFont('Consolas', 9))
        info_layout.addWidget(self._lbl_status, 3, 1)

        info_layout.addWidget(_grey('Active Preset:'), 4, 0)
        self._lbl_preset = QLabel('—')
        self._lbl_preset.setFont(QFont('Consolas', 9))
        info_layout.addWidget(self._lbl_preset, 4, 1)

        self._fix_lbl = QLabel('⚠  Folder name does not match expected format — a "Fix Folder Name" dialog will appear when you run an operation.')
        self._fix_lbl.setFont(QFont('Segoe UI', 8))
        self._fix_lbl.setStyleSheet('color: #b45309;')
        self._fix_lbl.setWordWrap(True)
        self._fix_lbl.hide()
        info_layout.addWidget(self._fix_lbl, 5, 0, 1, 2)

        layout.addWidget(self._info_frame)

        layout.addWidget(_separator())

        # ── Actions ───────────────────────────────────────────────────────────
        layout.addWidget(_bold('Operations'))

        btn_grid = QGridLayout()
        btn_grid.setSpacing(8)

        self._rename_btn = QPushButton('Rename Media Files')
        self._rename_btn.setMinimumHeight(36)
        self._rename_btn.setStyleSheet(
            'background-color: #1565C0; color: white; font-weight: bold; font-size: 9pt;'
        )
        self._rename_btn.setEnabled(False)
        self._rename_btn.clicked.connect(self._run_rename)
        btn_grid.addWidget(self._rename_btn, 0, 0, 1, 2)

        self._today_btn = QPushButton('Update Folder Date  →  Today')
        self._today_btn.setMinimumHeight(32)
        self._today_btn.setStyleSheet('font-size: 9pt;')
        self._today_btn.setEnabled(False)
        self._today_btn.clicked.connect(self._run_today)
        btn_grid.addWidget(self._today_btn, 1, 0)

        self._latest_btn = QPushButton('Update Folder Date  →  Latest Media Date')
        self._latest_btn.setMinimumHeight(32)
        self._latest_btn.setStyleSheet('font-size: 9pt;')
        self._latest_btn.setEnabled(False)
        self._latest_btn.clicked.connect(self._run_latest)
        btn_grid.addWidget(self._latest_btn, 1, 1)

        layout.addLayout(btn_grid)

        layout.addWidget(_separator())

        # ── Result log ────────────────────────────────────────────────────────
        layout.addWidget(_bold('Result'))
        self._result_lbl = QLabel('No operation run yet.')
        self._result_lbl.setFont(QFont('Segoe UI', 9))
        self._result_lbl.setStyleSheet('color: #555; padding: 6px; background: #fafafa; border: 1px solid #eee;')
        self._result_lbl.setWordWrap(True)
        self._result_lbl.setMinimumHeight(48)
        layout.addWidget(self._result_lbl)

        layout.addStretch()

    # ── Folder change ─────────────────────────────────────────────────────────

    def _browse_folder(self):
        path = QFileDialog.getExistingDirectory(self, 'Select Creator Folder')
        if path:
            self._folder_edit.setText(os.path.normpath(path))

    def _on_folder_changed(self, path: str):
        from core.folder import parse_creator_folder
        from core.config import get_active_preset

        path = path.strip().rstrip('\\/').rstrip('/')
        is_valid_dir = os.path.isdir(path)

        if not is_valid_dir:
            self._lbl_creator.setText('—')
            self._lbl_category.setText('—')
            self._lbl_date.setText('—')
            self._lbl_status.setText('—')
            self._lbl_preset.setText('—')
            self._fix_lbl.hide()
            self._set_btns_enabled(False)
            return

        folder_name = os.path.basename(path)
        creator, date_str, category, status = parse_creator_folder(folder_name)

        preset = get_active_preset(self._config)
        self._lbl_preset.setText(preset.get('name', '—'))

        if creator:
            self._lbl_creator.setText(creator)
            self._lbl_category.setText(category or '—')
            self._lbl_date.setText(date_str or '—')
            self._lbl_status.setText(status or 'None')
            self._fix_lbl.hide()
        else:
            self._lbl_creator.setText('(unrecognized)')
            self._lbl_category.setText('(unrecognized)')
            self._lbl_date.setText('(unrecognized)')
            self._lbl_status.setText('(unrecognized)')
            self._fix_lbl.show()

        self._set_btns_enabled(True)

    def _set_btns_enabled(self, enabled: bool):
        self._rename_btn.setEnabled(enabled)
        self._today_btn.setEnabled(enabled)
        self._latest_btn.setEnabled(enabled)

    # ── Operations ────────────────────────────────────────────────────────────

    def _get_folder(self) -> str:
        return self._folder_edit.text().strip().rstrip('\\/').rstrip('/')

    def _run_rename(self):
        from core.folder import parse_creator_folder
        from core.config import get_active_preset
        from gui.fix_folder_dialog import FixFolderDialog
        from gui.rename_window import RenameWindow

        folder = self._get_folder()
        if not os.path.isdir(folder):
            self._set_result('⚠ Invalid folder path.', error=True)
            return

        config = self._config
        preset = get_active_preset(config)
        folder_name = os.path.basename(folder)
        creator, _date, category, _status = parse_creator_folder(folder_name)

        if creator is None:
            dlg = FixFolderDialog(folder_name, parent=self)
            if dlg.exec() != dlg.DialogCode.Accepted:
                return
            creator, _date, category, _status = dlg.result_values()
            if creator is None:
                return

        self._rename_win = RenameWindow(folder, creator, category, preset)
        self._rename_win.show()
        self._set_result(f'Rename window opened for:\n{folder}')

    def _run_today(self):
        from datetime import date
        from core.folder import parse_creator_folder, build_folder_name
        from core.config import get_active_preset
        from gui.fix_folder_dialog import FixFolderDialog
        from gui.confirm_dialog import ConfirmFolderRenameDialog

        folder = self._get_folder()
        if not os.path.isdir(folder):
            self._set_result('⚠ Invalid folder path.', error=True)
            return

        preset = get_active_preset(self._config)
        folder_name = os.path.basename(folder)
        parent_dir = os.path.dirname(folder)
        today_str = date.today().strftime('%Y-%m-%d')

        creator, old_date, category, status = parse_creator_folder(folder_name)

        if creator is None:
            dlg = FixFolderDialog(folder_name, date_str=today_str, parent=self)
            if dlg.exec() != dlg.DialogCode.Accepted:
                return
            creator, today_str, category, status = dlg.result_values()
            if creator is None:
                return
            old_date = None
        else:
            dlg = ConfirmFolderRenameDialog(
                creator, today_str, category, status,
                date_label="today's date", preset=preset, parent=self
            )
            if dlg.exec() != dlg.DialogCode.Accepted:
                return
            today_str = dlg.confirmed_date() or today_str

        if old_date == today_str:
            self._set_result('Folder date is already today — no change made.')
            return

        new_name = build_folder_name(creator, today_str, category, status, preset)
        new_path = os.path.join(parent_dir, new_name)
        try:
            os.rename(folder, new_path)
            self._folder_edit.setText(os.path.normpath(new_path))
            self._set_result(f'Folder renamed to:\n{new_name}')
        except Exception as e:
            self._set_result(f'⚠ Rename failed: {e}', error=True)

    def _run_latest(self):
        from core.folder import parse_creator_folder, build_folder_name, find_latest_date
        from core.config import get_active_preset, get_all_extensions
        from gui.fix_folder_dialog import FixFolderDialog
        from gui.confirm_dialog import ConfirmFolderRenameDialog

        folder = self._get_folder()
        if not os.path.isdir(folder):
            self._set_result('⚠ Invalid folder path.', error=True)
            return

        preset = get_active_preset(self._config)
        extensions = get_all_extensions(preset)
        folder_name = os.path.basename(folder)
        parent_dir = os.path.dirname(folder)

        self._set_result('Scanning for latest media date…')
        QApplication.processEvents()

        try:
            _dt, latest_date_str, latest_file = find_latest_date(folder, extensions)
        except Exception as e:
            self._set_result(f'⚠ Error scanning folder: {e}', error=True)
            return

        if not latest_date_str:
            self._set_result('⚠ No readable media creation date found in this folder.', error=True)
            return

        creator, old_date, category, status = parse_creator_folder(folder_name)

        if creator is None:
            dlg = FixFolderDialog(folder_name, date_str=latest_date_str,
                                  latest_file=latest_file or '', parent=self)
            if dlg.exec() != dlg.DialogCode.Accepted:
                return
            creator, latest_date_str, category, status = dlg.result_values()
            if creator is None:
                return
            old_date = None
        else:
            dlg = ConfirmFolderRenameDialog(
                creator, latest_date_str, category, status,
                date_label='latest media date',
                latest_file=latest_file or '',
                preset=preset, parent=self
            )
            if dlg.exec() != dlg.DialogCode.Accepted:
                return
            latest_date_str = dlg.confirmed_date() or latest_date_str

        if old_date == latest_date_str:
            self._set_result('Folder date already matches the latest media date — no change made.')
            return

        new_name = build_folder_name(creator, latest_date_str, category, status, preset)
        new_path = os.path.join(parent_dir, new_name)
        try:
            os.rename(folder, new_path)
            self._folder_edit.setText(os.path.normpath(new_path))
            self._set_result(
                f'Folder renamed to:\n{new_name}'
                + (f'\n\nLatest date from: {latest_file}' if latest_file else '')
            )
        except Exception as e:
            self._set_result(f'⚠ Rename failed: {e}', error=True)

    def _set_result(self, msg: str, error: bool = False):
        self._result_lbl.setText(msg)
        color = '#c00' if error else '#1B5E20'
        self._result_lbl.setStyleSheet(
            f'color: {color}; padding: 6px; background: #fafafa; border: 1px solid #eee;'
        )


# ── Presets Tab ───────────────────────────────────────────────────────────────

class _PresetsTab(QWidget):
    def __init__(self, config: dict, dirty_cb):
        super().__init__()
        self._config = config
        self._dirty_cb = dirty_cb
        self._current_preset = None
        self._loading = False
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 8)
        layout.setSpacing(8)

        # ── Preset selector row ───────────────────────────────────────────────
        sel_row = QHBoxLayout()
        sel_row.addWidget(_bold('Active Preset:'))
        self._preset_combo = QComboBox()
        self._preset_combo.setMinimumWidth(200)
        self._preset_combo.currentTextChanged.connect(self._on_preset_selected)
        sel_row.addWidget(self._preset_combo)
        sel_row.addSpacing(10)

        new_btn = QPushButton('New Preset')
        new_btn.clicked.connect(self._new_preset)
        dup_btn = QPushButton('Duplicate')
        dup_btn.clicked.connect(self._duplicate_preset)
        self._del_btn = QPushButton('Delete')
        self._del_btn.clicked.connect(self._delete_preset)
        self._del_btn.setStyleSheet('color: #c00;')

        sel_row.addWidget(new_btn)
        sel_row.addWidget(dup_btn)
        sel_row.addWidget(self._del_btn)
        sel_row.addStretch()
        layout.addLayout(sel_row)

        layout.addWidget(_separator())

        # ── Main form + live preview (side by side) ───────────────────────────
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # Left: form
        form_scroll = QScrollArea()
        form_scroll.setWidgetResizable(True)
        form_scroll.setFrameShape(QFrame.Shape.NoFrame)
        form_widget = QWidget()
        self._form_layout = QGridLayout(form_widget)
        self._form_layout.setColumnStretch(1, 1)
        self._form_layout.setSpacing(6)
        self._form_layout.setContentsMargins(4, 4, 4, 4)
        form_scroll.setWidget(form_widget)

        row = 0

        def add_field(label_text, widget, hint=''):
            self._form_layout.addWidget(_bold(label_text), row, 0,
                                        Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignRight)
            self._form_layout.addWidget(widget, row, 1)
            if hint:
                hint_lbl = QLabel(hint)
                hint_lbl.setFont(QFont('Segoe UI', 7))
                hint_lbl.setStyleSheet('color: #999;')
                hint_lbl.setWordWrap(True)
                self._form_layout.addWidget(hint_lbl, row + 1, 1)
                return row + 2
            return row + 1

        # Name
        self._name_edit = QLineEdit()
        self._name_edit.textChanged.connect(self._on_field_changed)
        row = add_field('Name:', self._name_edit)

        # Description
        self._desc_edit = QLineEdit()
        self._desc_edit.textChanged.connect(self._on_field_changed)
        row = add_field('Description:', self._desc_edit)

        # File template
        self._file_tmpl_edit = QLineEdit()
        self._file_tmpl_edit.textChanged.connect(self._on_field_changed)
        vars_hint = (
            'Variables: {creator}  {creator_jp}  {date}  {post_title}  '
            '{original_name}  {category}  {subfolder_path}  {status}'
        )
        row = add_field('File Template:', self._file_tmpl_edit, vars_hint)

        # Folder template
        self._folder_tmpl_edit = QLineEdit()
        self._folder_tmpl_edit.textChanged.connect(self._on_field_changed)
        row = add_field('Folder Template:', self._folder_tmpl_edit)

        # Status suffix
        self._status_suffix_edit = QLineEdit()
        self._status_suffix_edit.textChanged.connect(self._on_field_changed)
        row = add_field('Status Suffix:', self._status_suffix_edit,
                        'Appended to folder name when status is set. e.g.  [{status}]')

        # Date format — fixed, not editable
        date_fixed_lbl = QLabel('YYYY-MM-DD  (fixed — cannot be changed)')
        date_fixed_lbl.setFont(QFont('Segoe UI', 8))
        date_fixed_lbl.setStyleSheet('color: #999;')
        row = add_field('Date Format:', date_fixed_lbl)

        # Subfolder separator
        self._sep_edit = QLineEdit()
        self._sep_edit.textChanged.connect(self._on_field_changed)
        row = add_field('Subfolder Separator:', self._sep_edit)

        # Checkboxes
        self._include_sub_cb = QCheckBox('Include subfolder path in filename')
        self._include_sub_cb.stateChanged.connect(self._on_field_changed)
        self._form_layout.addWidget(self._include_sub_cb, row, 1)
        row += 1

        self._skip_named_cb = QCheckBox('Skip files already correctly named')
        self._skip_named_cb.stateChanged.connect(self._on_field_changed)
        self._form_layout.addWidget(self._skip_named_cb, row, 1)
        row += 1

        # Date source priority (simple list with up/down)
        self._form_layout.addWidget(_bold('Date Priority:'), row, 0,
                                    Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignRight)
        prio_widget = QWidget()
        prio_layout = QHBoxLayout(prio_widget)
        prio_layout.setContentsMargins(0, 0, 0, 0)
        self._prio_list = QListWidget()
        self._prio_list.setFixedHeight(72)
        self._prio_list.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        prio_layout.addWidget(self._prio_list)
        prio_btns = QVBoxLayout()
        self._prio_up_btn = QPushButton('↑')
        self._prio_up_btn.setFixedSize(28, 28)
        self._prio_up_btn.clicked.connect(self._prio_up)
        self._prio_dn_btn = QPushButton('↓')
        self._prio_dn_btn.setFixedSize(28, 28)
        self._prio_dn_btn.clicked.connect(self._prio_down)
        prio_btns.addWidget(self._prio_up_btn)
        prio_btns.addWidget(self._prio_dn_btn)
        prio_btns.addStretch()
        prio_layout.addLayout(prio_btns)
        self._form_layout.addWidget(prio_widget, row, 1)
        row += 1

        # Right: live preview
        preview_widget = QWidget()
        preview_layout = QVBoxLayout(preview_widget)
        preview_layout.setContentsMargins(12, 4, 4, 4)
        preview_layout.setSpacing(6)

        preview_layout.addWidget(_bold('Live Preview'))
        preview_layout.addWidget(_separator())

        grid = QGridLayout()
        grid.setSpacing(4)

        def pv_field(label, attr, placeholder=''):
            lbl = QLabel(label)
            lbl.setFont(QFont('Segoe UI', 8))
            edit = QLineEdit()
            edit.setPlaceholderText(placeholder)
            edit.setFont(QFont('Segoe UI', 8))
            edit.textChanged.connect(self._update_preview)
            setattr(self, attr, edit)
            return lbl, edit

        r = 0
        for label, attr, ph in [
            ('Creator:', '_pv_creator', 'FanFan'),
            ('Creator JP:', '_pv_creator_jp', '白魚'),
            ('Category:', '_pv_category', 'Fanbox'),
            ('Date:', '_pv_date', '2024-06-01'),
            ('Post Title:', '_pv_post_title', 'June Pack'),
            ('Original Name:', '_pv_orig', 'video_001'),
            ('Subfolder:', '_pv_sub', 'Pack01'),
            ('Status:', '_pv_status', 'Obtained'),
        ]:
            lbl, edit = pv_field(label, attr, ph)
            grid.addWidget(lbl, r, 0, Qt.AlignmentFlag.AlignRight)
            grid.addWidget(edit, r, 1)
            r += 1

        preview_layout.addLayout(grid)
        preview_layout.addWidget(_separator())

        preview_layout.addWidget(_bold('File output (no subfolder):'))
        self._pv_file_out = QLabel('—')
        self._pv_file_out.setFont(QFont('Consolas', 8))
        self._pv_file_out.setStyleSheet('color: #1565C0; padding: 4px; background: #f0f4ff;')
        self._pv_file_out.setWordWrap(True)
        preview_layout.addWidget(self._pv_file_out)

        preview_layout.addWidget(_bold('File output (with subfolder):'))
        self._pv_file_out_sub = QLabel('—')
        self._pv_file_out_sub.setFont(QFont('Consolas', 8))
        self._pv_file_out_sub.setStyleSheet('color: #4527A0; padding: 4px; background: #f3f0ff;')
        self._pv_file_out_sub.setWordWrap(True)
        preview_layout.addWidget(self._pv_file_out_sub)

        preview_layout.addWidget(_bold('Folder output:'))
        self._pv_folder_out = QLabel('—')
        self._pv_folder_out.setFont(QFont('Consolas', 8))
        self._pv_folder_out.setStyleSheet('color: #2E7D32; padding: 4px; background: #f0fff0;')
        self._pv_folder_out.setWordWrap(True)
        preview_layout.addWidget(self._pv_folder_out)

        preview_layout.addStretch()

        splitter.addWidget(form_scroll)
        splitter.addWidget(preview_widget)
        splitter.setSizes([480, 320])
        layout.addWidget(splitter, 1)

    # ── Load / Save ───────────────────────────────────────────────────────────

    def load(self, config: dict):
        self._loading = True
        self._config = config
        self._preset_combo.clear()
        active_name = config.get('active_preset', '')
        for i, p in enumerate(config.get('presets', [])):
            self._preset_combo.addItem(p['name'])
            if p['name'] == active_name:
                self._preset_combo.setCurrentIndex(i)
        self._loading = False
        self._on_preset_selected(self._preset_combo.currentText())

    def save_to(self, config: dict):
        # Save current form values back to current preset
        if self._current_preset is not None:
            self._flush_form_to_preset(self._current_preset)
        config['active_preset'] = self._preset_combo.currentText()

    def _flush_form_to_preset(self, preset: dict):
        if preset.get('builtin', False):
            return  # builtin presets are read-only — never overwrite
        preset['name'] = self._name_edit.text().strip()
        preset['description'] = self._desc_edit.text().strip()
        preset['file_template'] = self._file_tmpl_edit.text().strip()
        preset['folder_template'] = self._folder_tmpl_edit.text().strip()
        preset['folder_status_suffix'] = self._status_suffix_edit.text()
        preset['date_format'] = '%Y-%m-%d'  # always fixed
        preset['subfolder_separator'] = self._sep_edit.text()
        preset['include_subfolder_in_name'] = self._include_sub_cb.isChecked()
        preset['skip_already_named'] = self._skip_named_cb.isChecked()
        preset['date_source_priority'] = [
            self._prio_list.item(i).text()
            for i in range(self._prio_list.count())
        ]

    def _load_form_from_preset(self, preset: dict):
        self._loading = True
        self._name_edit.setText(preset.get('name', ''))
        self._desc_edit.setText(preset.get('description', ''))
        self._file_tmpl_edit.setText(preset.get('file_template', ''))
        self._folder_tmpl_edit.setText(preset.get('folder_template', ''))
        self._status_suffix_edit.setText(preset.get('folder_status_suffix', ' [{status}]'))
        self._sep_edit.setText(preset.get('subfolder_separator', ' - '))
        self._include_sub_cb.setChecked(preset.get('include_subfolder_in_name', True))
        self._skip_named_cb.setChecked(preset.get('skip_already_named', True))

        self._prio_list.clear()
        for item in preset.get('date_source_priority', ['metadata', 'filename', 'null']):
            self._prio_list.addItem(item)

        is_builtin = preset.get('builtin', False)
        self._del_btn.setEnabled(not is_builtin)
        self._set_form_editable(not is_builtin)

        self._loading = False
        self._update_preview()

    def _set_form_editable(self, editable: bool):
        """Enable or disable all form editing widgets."""
        for widget in (self._name_edit, self._desc_edit, self._file_tmpl_edit,
                       self._folder_tmpl_edit, self._status_suffix_edit, self._sep_edit):
            widget.setReadOnly(not editable)
            widget.setStyleSheet('' if editable else 'background: #f5f5f5; color: #999;')
        for widget in (self._include_sub_cb, self._skip_named_cb,
                       self._prio_list, self._prio_up_btn, self._prio_dn_btn):
            widget.setEnabled(editable)

    # ── Slots ─────────────────────────────────────────────────────────────────

    def _on_preset_selected(self, name: str):
        if self._loading:
            return
        # Flush previous preset changes
        if self._current_preset is not None:
            self._flush_form_to_preset(self._current_preset)

        for p in self._config.get('presets', []):
            if p['name'] == name:
                self._current_preset = p
                self._load_form_from_preset(p)
                return

    def _on_field_changed(self, *_):
        if not self._loading:
            self._dirty_cb()
            self._update_preview()

    def _update_preview(self, *_):
        from core.renamer import render_template
        from core.folder import build_folder_name

        file_tmpl = self._file_tmpl_edit.text()
        folder_tmpl = self._folder_tmpl_edit.text()
        status_suffix = self._status_suffix_edit.text()
        separator = self._sep_edit.text() or ' - '
        include_sub = self._include_sub_cb.isChecked()

        creator = self._pv_creator.text() or 'Creator'
        creator_jp = self._pv_creator_jp.text()
        category = self._pv_category.text() or 'Fanbox'
        date_str = self._pv_date.text() or '2024-06-01'
        post_title = self._pv_post_title.text()
        orig = self._pv_orig.text() or 'filename'
        sub = self._pv_sub.text()
        status = self._pv_status.text()

        try:
            # Date format is always YYYY-MM-DD — no conversion needed
            formatted_date = date_str or '2024-06-01'

            # Without subfolder
            variables_flat = {
                'creator': creator, 'creator_jp': creator_jp,
                'date': formatted_date, 'post_title': post_title,
                'original_name': orig, 'category': category,
                'source': category,
            }
            file_out = render_template(file_tmpl, variables_flat) + '.ext'
            self._pv_file_out.setText(file_out)

            # With subfolder (always show using sample subfolder or fallback label)
            sample_sub = sub or 'Pack01'
            sub_name = (sample_sub + separator + orig) if include_sub else orig
            variables_sub = dict(variables_flat, original_name=sub_name)
            file_out_sub = render_template(file_tmpl, variables_sub) + '.ext'
            sub_note = '' if include_sub else '  [subfolder embedding disabled]'
            self._pv_file_out_sub.setText(file_out_sub + sub_note)

            # Folder preview
            dummy_preset = {
                'folder_template': folder_tmpl,
                'folder_status_suffix': status_suffix,
            }
            folder_out = build_folder_name(creator, formatted_date, category,
                                           status or None, dummy_preset)
            self._pv_folder_out.setText(folder_out)
        except Exception as e:
            self._pv_file_out.setText(f'[error: {e}]')
            self._pv_file_out_sub.setText('')
            self._pv_folder_out.setText('')

    def _prio_up(self):
        row = self._prio_list.currentRow()
        if row > 0:
            item = self._prio_list.takeItem(row)
            self._prio_list.insertItem(row - 1, item)
            self._prio_list.setCurrentRow(row - 1)
            self._dirty_cb()

    def _prio_down(self):
        row = self._prio_list.currentRow()
        if row < self._prio_list.count() - 1:
            item = self._prio_list.takeItem(row)
            self._prio_list.insertItem(row + 1, item)
            self._prio_list.setCurrentRow(row + 1)
            self._dirty_cb()

    def _new_preset(self):
        template = copy.deepcopy(DEFAULT_CONFIG['presets'][2])  # Cleanup preset as base
        template['name'] = 'New Preset'
        template['builtin'] = False
        self._config['presets'].append(template)
        self._preset_combo.addItem(template['name'])
        self._preset_combo.setCurrentText(template['name'])
        self._dirty_cb()

    def _duplicate_preset(self):
        if self._current_preset is None:
            return
        self._flush_form_to_preset(self._current_preset)
        new_preset = copy.deepcopy(self._current_preset)
        new_preset['name'] = new_preset['name'] + ' (Copy)'
        new_preset['builtin'] = False
        self._config['presets'].append(new_preset)
        self._preset_combo.addItem(new_preset['name'])
        self._preset_combo.setCurrentText(new_preset['name'])
        self._dirty_cb()

    def _delete_preset(self):
        if self._current_preset is None or self._current_preset.get('builtin'):
            return
        name = self._current_preset['name']
        if len(self._config.get('presets', [])) <= 1:
            QMessageBox.warning(self, 'Cannot Delete', 'At least one preset must remain.')
            return
        self._config['presets'] = [
            p for p in self._config['presets'] if p['name'] != name
        ]
        idx = self._preset_combo.currentIndex()
        self._preset_combo.removeItem(idx)
        self._current_preset = None
        self._dirty_cb()


# ── Context Menu Tab ──────────────────────────────────────────────────────────

class _ContextMenuTab(QWidget):
    def __init__(self, config: dict, dirty_cb):
        super().__init__()
        self._config = config
        self._dirty_cb = dirty_cb
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 8)
        layout.setSpacing(8)

        layout.addWidget(QLabel(
            'Configure the context menu entries. '
            'Click "Apply to Registry" to update Windows after making changes.'
        ))
        layout.addWidget(_separator())

        # Table: Order | Enabled | Label | Trigger | Icon
        self._table = QTableWidget(0, 5)
        self._table.setHorizontalHeaderLabels(['Order', 'Enabled', 'Label', 'Trigger', 'Icon'])
        self._table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        self._table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        self._table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self._table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
        self._table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
        self._table.setColumnWidth(0, 70)
        self._table.setColumnWidth(1, 65)
        self._table.setColumnWidth(3, 100)
        self._table.verticalHeader().setVisible(False)
        self._table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self._table.setEditTriggers(QAbstractItemView.EditTrigger.DoubleClicked
                                    | QAbstractItemView.EditTrigger.SelectedClicked)
        layout.addWidget(self._table, 1)

        apply_btn = QPushButton('Apply to Registry  (requires admin elevation)')
        apply_btn.setStyleSheet('background-color: #1565C0; color: white; font-weight: bold; padding: 6px 12px;')
        apply_btn.clicked.connect(self._apply_registry)

        note = QLabel('Note: Windows will prompt for administrator permission when applying.')
        note.setFont(QFont('Segoe UI', 8))
        note.setStyleSheet('color: #888;')

        layout.addWidget(apply_btn)
        layout.addWidget(note)

    def load(self, config: dict):
        self._config = config
        items = sorted(
            config.get('context_menu', {}).get('items', []),
            key=lambda x: x.get('sort_order', 99)
        )
        self._table.setRowCount(len(items))

        for row, item in enumerate(items):
            # Order buttons
            order_widget = QWidget()
            order_layout = QHBoxLayout(order_widget)
            order_layout.setContentsMargins(2, 0, 2, 0)
            up_btn = QPushButton('↑')
            up_btn.setFixedSize(26, 22)
            up_btn.clicked.connect(lambda _, r=row: self._move_row(r, -1))
            dn_btn = QPushButton('↓')
            dn_btn.setFixedSize(26, 22)
            dn_btn.clicked.connect(lambda _, r=row: self._move_row(r, 1))
            order_layout.addWidget(up_btn)
            order_layout.addWidget(dn_btn)
            self._table.setCellWidget(row, 0, order_widget)

            # Enabled checkbox
            cb = QCheckBox()
            cb.setChecked(item.get('enabled', True))
            cb.stateChanged.connect(self._dirty_cb)
            cb_widget = QWidget()
            cb_layout = QHBoxLayout(cb_widget)
            cb_layout.addWidget(cb)
            cb_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            cb_layout.setContentsMargins(0, 0, 0, 0)
            self._table.setCellWidget(row, 1, cb_widget)

            # Label (editable)
            lbl_item = QTableWidgetItem(item.get('label', ''))
            self._table.setItem(row, 2, lbl_item)

            # Trigger (read-only display)
            trigger_item = QTableWidgetItem(item.get('trigger', 'background').capitalize())
            trigger_item.setFlags(trigger_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self._table.setItem(row, 3, trigger_item)

            # Icon path + Browse button
            icon_widget = QWidget()
            icon_layout = QHBoxLayout(icon_widget)
            icon_layout.setContentsMargins(2, 0, 2, 0)
            icon_edit = QLineEdit(item.get('icon', ''))
            icon_edit.setFont(QFont('Segoe UI', 8))
            browse_btn = QPushButton('…')
            browse_btn.setFixedWidth(26)
            browse_btn.clicked.connect(lambda _, e=icon_edit: self._browse_icon(e))
            icon_layout.addWidget(icon_edit)
            icon_layout.addWidget(browse_btn)
            self._table.setCellWidget(row, 4, icon_widget)

        self._table.resizeRowsToContents()

    def save_to(self, config: dict):
        items = sorted(
            config.get('context_menu', {}).get('items', []),
            key=lambda x: x.get('sort_order', 99)
        )
        for row in range(min(self._table.rowCount(), len(items))):
            item = items[row]
            # Enabled
            cb_widget = self._table.cellWidget(row, 1)
            if cb_widget:
                cb = cb_widget.findChild(QCheckBox)
                if cb:
                    item['enabled'] = cb.isChecked()
            # Label
            lbl_item = self._table.item(row, 2)
            if lbl_item:
                item['label'] = lbl_item.text()
            # Icon
            icon_widget = self._table.cellWidget(row, 4)
            if icon_widget:
                edit = icon_widget.findChild(QLineEdit)
                if edit:
                    item['icon'] = edit.text()
            item['sort_order'] = row + 1

    def _browse_icon(self, edit: QLineEdit):
        path, _ = QFileDialog.getOpenFileName(
            self, 'Select Icon', '', 'Icon Files (*.ico);;All Files (*)'
        )
        if path:
            # Store relative path if inside script dir
            script_dir = os.path.dirname(os.path.abspath(__file__))
            try:
                rel = os.path.relpath(path, script_dir)
                edit.setText(rel)
            except ValueError:
                edit.setText(path)
            self._dirty_cb()

    def _move_row(self, row: int, direction: int):
        items = self._config.get('context_menu', {}).get('items', [])
        target = row + direction
        if 0 <= target < len(items):
            items[row]['sort_order'], items[target]['sort_order'] = (
                items[target]['sort_order'], items[row]['sort_order']
            )
            self.load(self._config)
            self._dirty_cb()

    def _apply_registry(self):
        # Save current state first
        self.save_to(self._config)
        save_config(self._config)

        script = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                              'install_helper.py')
        try:
            subprocess.run([sys.executable, script, '--install', '--elevate'],
                           check=False)
            QMessageBox.information(self, 'Registry Updated',
                                    'Context menu entries have been updated.')
        except Exception as e:
            QMessageBox.critical(self, 'Error', f'Failed to apply registry:\n{e}')


# ── File Types Tab ────────────────────────────────────────────────────────────

class _FileTypesTab(QWidget):
    def __init__(self, config: dict, dirty_cb):
        super().__init__()
        self._config = config
        self._dirty_cb = dirty_cb
        self._checkboxes: dict = {}  # ext → QCheckBox
        self._active_preset_name = ''
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 8)
        layout.setSpacing(8)

        # Preset selector
        top_row = QHBoxLayout()
        top_row.addWidget(_bold('Editing extensions for preset:'))
        self._preset_combo = QComboBox()
        self._preset_combo.setMinimumWidth(200)
        self._preset_combo.currentTextChanged.connect(self._on_preset_changed)
        top_row.addWidget(self._preset_combo)
        top_row.addStretch()
        layout.addLayout(top_row)
        layout.addWidget(_separator())

        # Extension groups
        self._video_group = _ExtGroup('Video Files', self._dirty_cb)
        self._image_group = _ExtGroup('Image Files', self._dirty_cb)
        self._other_group = _ExtGroup('Other', self._dirty_cb)

        for group in (self._video_group, self._image_group, self._other_group):
            layout.addWidget(group)

        # HEIC note
        from core.metadata import HEIC_SUPPORTED
        heic_note = QLabel(
            f'HEIC support: {"✓ Available (pillow-heif installed)" if HEIC_SUPPORTED else "✗ Not available — install pillow-heif for .heic support"}'
        )
        heic_note.setFont(QFont('Segoe UI', 8))
        heic_note.setStyleSheet('color: #2E7D32;' if HEIC_SUPPORTED else 'color: #c00;')
        layout.addWidget(heic_note)

        # Add custom extension
        add_row = QHBoxLayout()
        add_row.addWidget(_bold('Add custom:'))
        self._custom_ext_edit = QLineEdit()
        self._custom_ext_edit.setPlaceholderText('.ext')
        self._custom_ext_edit.setFixedWidth(80)
        add_btn = QPushButton('Add')
        add_btn.setFixedWidth(60)
        add_btn.clicked.connect(self._add_custom)
        add_row.addWidget(self._custom_ext_edit)
        add_row.addWidget(add_btn)
        add_row.addStretch()
        layout.addLayout(add_row)

        layout.addStretch()

    def load(self, config: dict):
        self._config = config
        self._preset_combo.blockSignals(True)
        self._preset_combo.clear()
        active_name = config.get('active_preset', '')
        for p in config.get('presets', []):
            self._preset_combo.addItem(p['name'])
        self._preset_combo.setCurrentText(active_name)
        self._preset_combo.blockSignals(False)
        self._on_preset_changed(self._preset_combo.currentText())

    def _on_preset_changed(self, name: str):
        self._active_preset_name = name
        for p in self._config.get('presets', []):
            if p['name'] == name:
                exts = p.get('supported_extensions', {})
                self._video_group.set_extensions(exts.get('video', []))
                self._image_group.set_extensions(exts.get('image', []))
                self._other_group.set_extensions(exts.get('other', []))
                return

    def save_to(self, config: dict):
        for p in config.get('presets', []):
            if p['name'] == self._active_preset_name:
                p['supported_extensions'] = {
                    'video': self._video_group.get_enabled(),
                    'image': self._image_group.get_enabled(),
                    'other': self._other_group.get_enabled(),
                }
                return

    def _add_custom(self):
        ext = self._custom_ext_edit.text().strip().lower()
        if not ext.startswith('.'):
            ext = '.' + ext
        if ext:
            self._other_group.add_extension(ext, enabled=True)
            self._custom_ext_edit.clear()
            self._dirty_cb()


class _ExtGroup(QGroupBox):
    def __init__(self, title: str, dirty_cb):
        super().__init__(title)
        self._dirty_cb = dirty_cb
        self._checkboxes: list = []
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)
        self._inner = layout

    def set_extensions(self, extensions: list):
        # Clear existing
        for cb in self._checkboxes:
            self._inner.removeWidget(cb)
            cb.deleteLater()
        self._checkboxes = []

        for ext in extensions:
            self.add_extension(ext, enabled=True)
        self._inner.addStretch()

    def add_extension(self, ext: str, enabled: bool = True):
        cb = QCheckBox(ext)
        cb.setChecked(enabled)
        cb.stateChanged.connect(self._dirty_cb)
        self._inner.addWidget(cb)
        self._checkboxes.append(cb)

    def get_enabled(self) -> list:
        return [cb.text() for cb in self._checkboxes if cb.isChecked()]


# ── About Tab ─────────────────────────────────────────────────────────────────

class _AboutTab(QWidget):
    def __init__(self):
        super().__init__()
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(12)

        title = QLabel('MediaRenamer')
        title.setFont(QFont('Segoe UI', 18, QFont.Weight.Bold))
        layout.addWidget(title)

        desc = QLabel(
            'Rename and organize media files based on internal creation date metadata.\n'
            'Enforces the Universal Naming Standard for creator archives.\n\n'
            'Supports video, image, and GIF files.\n'
            'Context menu integration for Windows Explorer.'
        )
        desc.setFont(QFont('Segoe UI', 9))
        desc.setWordWrap(True)
        layout.addWidget(desc)

        layout.addWidget(_separator())

        re_reg_btn = QPushButton('Re-register Context Menu Entries')
        re_reg_btn.setFixedWidth(260)
        re_reg_btn.clicked.connect(self._re_register)
        layout.addWidget(re_reg_btn)

        readme_btn = QPushButton('Open README')
        readme_btn.setFixedWidth(260)
        readme_btn.clicked.connect(self._open_readme)
        layout.addWidget(readme_btn)

        layout.addStretch()

    def _re_register(self):
        script = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                              'install_helper.py')
        try:
            subprocess.run([sys.executable, script, '--install', '--elevate'],
                           check=False)
            QMessageBox.information(self, 'Done', 'Context menu entries re-registered.')
        except Exception as e:
            QMessageBox.critical(self, 'Error', str(e))

    def _open_readme(self):
        readme = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'README.md')
        if os.path.isfile(readme):
            os.startfile(readme)
        else:
            QMessageBox.information(self, 'Not Found', 'README.md not found.')


# ── Helpers ───────────────────────────────────────────────────────────────────

def _bold(text: str) -> QLabel:
    lbl = QLabel(text)
    lbl.setFont(QFont('Segoe UI', 9, QFont.Weight.Bold))
    return lbl


def _grey(text: str) -> QLabel:
    lbl = QLabel(text)
    lbl.setFont(QFont('Segoe UI', 8))
    lbl.setStyleSheet('color: #888;')
    return lbl


def _separator() -> QFrame:
    line = QFrame()
    line.setFrameShape(QFrame.Shape.HLine)
    line.setStyleSheet('color: #ddd;')
    return line


# ── Entry point ───────────────────────────────────────────────────────────────

def main():
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    window = SettingsWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
