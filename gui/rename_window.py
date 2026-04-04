"""
gui/rename_window.py — Main PyQt6 rename preview window.
Replaces the tkinter PreviewWindow in the old rename_media.py.
"""

import os

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QTableWidget, QTableWidgetItem, QHeaderView,
    QPushButton, QProgressBar, QMessageBox, QCheckBox, QAbstractItemView,
    QDialog, QDialogButtonBox, QScrollArea
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QColor, QFont


# ── Worker thread ─────────────────────────────────────────────────────────────

class _ScanWorker(QThread):
    """Builds the rename plan in a background thread."""
    finished = pyqtSignal(list, str)   # plan, error_message

    def __init__(self, folder: str, creator: str, creator_jp: str,
                 post_title: str, category: str, preset: dict):
        super().__init__()
        self._folder = folder
        self._creator = creator
        self._creator_jp = creator_jp
        self._post_title = post_title
        self._category = category
        self._preset = preset

    def run(self):
        try:
            from core.renamer import build_rename_plan
            plan = build_rename_plan(
                self._folder, self._creator, self._creator_jp,
                self._post_title, self._category, self._preset
            )
            self.finished.emit(plan, '')
        except Exception as e:
            self.finished.emit([], str(e))


# ── Main window ───────────────────────────────────────────────────────────────

class RenameWindow(QMainWindow):
    """
    Preview window showing files to be renamed with checkboxes.

    Constructor args:
        folder_path: absolute path to the creator folder
        creator:     creator name (parsed from folder)
        category:    category/source tag (parsed from folder)
        preset:      active preset dict
    """

    def __init__(self, folder_path: str, creator: str, category: str, preset: dict):
        super().__init__()
        self._folder_path = folder_path
        self._creator = creator
        self._category = category
        self._preset = preset
        self._plan = []
        self._worker = None

        self.setWindowTitle('Rename Media Files')
        self.setMinimumSize(760, 480)
        self.resize(960, 600)

        self._build_ui()
        self._start_scan()

    # ── UI construction ───────────────────────────────────────────────────────

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root_layout = QVBoxLayout(central)
        root_layout.setSpacing(6)
        root_layout.setContentsMargins(12, 10, 12, 10)

        # ── Optional fields bar (creator_jp, post_title) ─────────────────────
        has_jp = '{creator_jp}' in self._preset.get('file_template', '')
        has_title = '{post_title}' in self._preset.get('file_template', '')

        if has_jp or has_title:
            opt_row = QHBoxLayout()
            if has_jp:
                opt_row.addWidget(_bold_label('Creator JP:'))
                self._creator_jp_edit = QLineEdit()
                self._creator_jp_edit.setPlaceholderText('optional JP/native name')
                self._creator_jp_edit.setFixedWidth(180)
                opt_row.addWidget(self._creator_jp_edit)
                opt_row.addSpacing(12)
            else:
                self._creator_jp_edit = QLineEdit()  # hidden but accessible

            if has_title:
                opt_row.addWidget(_bold_label('Post Title:'))
                self._post_title_edit = QLineEdit()
                self._post_title_edit.setPlaceholderText('optional post title')
                self._post_title_edit.setFixedWidth(220)
                opt_row.addWidget(self._post_title_edit)
            else:
                self._post_title_edit = QLineEdit()

            opt_row.addStretch()
            root_layout.addLayout(opt_row)
        else:
            self._creator_jp_edit = QLineEdit()
            self._post_title_edit = QLineEdit()

        # ── Category / Source override ────────────────────────────────────────
        src_row = QHBoxLayout()
        src_row.addWidget(_bold_label('Category:'))
        self._category_edit = QLineEdit(self._category)
        self._category_edit.setFixedWidth(160)
        src_row.addWidget(self._category_edit)
        src_row.addWidget(QLabel('  (overrides the category tag in each filename)'))
        src_row.addStretch()
        root_layout.addLayout(src_row)

        # ── Status label ──────────────────────────────────────────────────────
        self._status_lbl = QLabel('Scanning files…')
        self._status_lbl.setFont(QFont('Segoe UI', 10, QFont.Weight.Bold))
        root_layout.addWidget(self._status_lbl)

        # ── Progress bar ──────────────────────────────────────────────────────
        self._progress = QProgressBar()
        self._progress.setRange(0, 0)   # indeterminate
        self._progress.setFixedHeight(6)
        self._progress.setTextVisible(False)
        root_layout.addWidget(self._progress)

        self._patience_lbl = QLabel(
            "This might take a while for large folders — hang tight."
        )
        self._patience_lbl.setFont(QFont('Segoe UI', 8))
        self._patience_lbl.setStyleSheet('color: #888;')
        root_layout.addWidget(self._patience_lbl)

        # ── File table ────────────────────────────────────────────────────────
        self._table = QTableWidget(0, 3)
        self._table.setHorizontalHeaderLabels(['', 'Original Name', 'New Name'])
        self._table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        self._table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self._table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self._table.setColumnWidth(0, 30)
        self._table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._table.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        self._table.verticalHeader().setVisible(False)
        self._table.setAlternatingRowColors(True)
        self._table.setFont(QFont('Consolas', 8))
        root_layout.addWidget(self._table, 1)

        # ── Button bar ────────────────────────────────────────────────────────
        btn_row = QHBoxLayout()

        self._select_all_btn = QPushButton('Select All')
        self._select_all_btn.setFixedWidth(90)
        self._select_all_btn.clicked.connect(self._select_all)

        self._deselect_all_btn = QPushButton('Deselect All')
        self._deselect_all_btn.setFixedWidth(90)
        self._deselect_all_btn.clicked.connect(self._deselect_all)

        self._deselect_null_btn = QPushButton('Deselect Null')
        self._deselect_null_btn.setFixedWidth(100)
        self._deselect_null_btn.setToolTip('Deselect files with no readable media creation date (shown in orange)')
        self._deselect_null_btn.clicked.connect(self._deselect_null)

        self._whats_null_btn = QPushButton("What's Null?")
        self._whats_null_btn.setFixedWidth(100)
        self._whats_null_btn.setToolTip('Learn what "null" dates mean and how dates are determined')
        self._whats_null_btn.clicked.connect(self._show_null_explainer)

        self._redate_btn = QPushButton('Manual Re-date')
        self._redate_btn.setFixedWidth(110)
        self._redate_btn.setToolTip('Manually assign a date to all selected files')
        self._redate_btn.setEnabled(False)
        self._redate_btn.clicked.connect(self._manual_redate)

        btn_row.addWidget(self._select_all_btn)
        btn_row.addWidget(self._deselect_all_btn)
        btn_row.addWidget(self._deselect_null_btn)
        btn_row.addSpacing(8)
        btn_row.addWidget(self._whats_null_btn)
        btn_row.addWidget(self._redate_btn)
        btn_row.addStretch()

        self._cancel_btn = QPushButton('Cancel')
        self._cancel_btn.setFixedWidth(100)
        self._cancel_btn.clicked.connect(self.close)
        self._confirm_btn = QPushButton('Confirm')
        self._confirm_btn.setFixedWidth(100)
        self._confirm_btn.setEnabled(False)
        self._confirm_btn.setStyleSheet('background-color: #4CAF50; color: white; font-weight: bold;')
        self._confirm_btn.clicked.connect(self._on_confirm)
        btn_row.addWidget(self._cancel_btn)
        btn_row.addWidget(self._confirm_btn)
        root_layout.addLayout(btn_row)

    # ── Scan ──────────────────────────────────────────────────────────────────

    def _start_scan(self):
        self._worker = _ScanWorker(
            self._folder_path, self._creator, '', '', self._category, self._preset
        )
        self._worker.finished.connect(self._on_scan_done)
        self._worker.start()

    def _on_scan_done(self, plan: list, error: str):
        self._progress.setRange(0, 1)
        self._progress.setValue(1)
        self._progress.hide()
        self._patience_lbl.hide()

        if error:
            self._status_lbl.setText('Error during scan.')
            QMessageBox.critical(self, 'Scan Error', error)
            return

        if not plan:
            self._status_lbl.setText('No files need renaming.')
            QMessageBox.information(self, 'Nothing to Rename', 'Nothing to Rename!')
            self.close()
            return

        self._plan = plan
        self._status_lbl.setText(f'Found {len(plan)} file(s) to rename.')
        self._populate_table()
        self._confirm_btn.setEnabled(True)
        self._redate_btn.setEnabled(True)

    # ── Table population ──────────────────────────────────────────────────────

    def _populate_table(self):
        null_color = QColor('#FF8C00')   # dark orange
        self._table.setRowCount(len(self._plan))
        self._checkboxes = []

        for row, item in enumerate(self._plan):
            # Checkbox column
            cb = QCheckBox()
            cb.setChecked(True)
            cb_widget = QWidget()
            cb_layout = QHBoxLayout(cb_widget)
            cb_layout.addWidget(cb)
            cb_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            cb_layout.setContentsMargins(0, 0, 0, 0)
            self._table.setCellWidget(row, 0, cb_widget)
            self._checkboxes.append(cb)

            # Old name
            old_item = QTableWidgetItem(item['old_name'])
            # New name
            new_item = QTableWidgetItem(item['new_name'])

            if item['is_null']:
                old_item.setForeground(null_color)
                new_item.setForeground(null_color)

            self._table.setItem(row, 1, old_item)
            self._table.setItem(row, 2, new_item)

        self._table.resizeRowsToContents()

    # ── Button handlers ───────────────────────────────────────────────────────

    def _select_all(self):
        for cb in getattr(self, '_checkboxes', []):
            cb.setChecked(True)

    def _deselect_all(self):
        for cb in getattr(self, '_checkboxes', []):
            cb.setChecked(False)

    def _deselect_null(self):
        for i, cb in enumerate(getattr(self, '_checkboxes', [])):
            if self._plan[i]['is_null']:
                cb.setChecked(False)

    def _show_null_explainer(self):
        dlg = QDialog(self)
        dlg.setWindowTitle("What's a Null Date?")
        dlg.setMinimumWidth(540)
        dlg.setMaximumWidth(580)

        layout = QVBoxLayout(dlg)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(12)

        text = QLabel()
        text.setWordWrap(True)
        text.setFont(QFont('Segoe UI', 9))
        text.setText(
            "<b>How Media Date Renamer decides which date to use</b><br><br>"

            "Every media file has two kinds of dates:<br><br>"

            "<b>1. File system dates</b> — the Created and Modified timestamps "
            "shown in Windows Explorer. These are <i>not</i> used by this tool. "
            "They are unreliable because they change every time you copy, move, "
            "download, re-compress, or re-upload a file. A video shot in 2019 "
            "that you downloaded yesterday will show yesterday's date — "
            "which tells you nothing about when it was actually made.<br><br>"

            "<b>2. Media creation date (embedded metadata)</b> — a date written "
            "into the file itself by the camera, recorder, or software that created it. "
            "This date travels with the file no matter how many times it is copied "
            "or moved. It is the closest reliable record of when the content was "
            "actually produced, which is why this tool reads it instead of "
            "the file system date.<br><br>"

            "<b>Where exactly does it look?</b><br>"
            "For <b>video files</b>, it reads the <i>encoded_date</i> or "
            "<i>tagged_date</i> field from the file's internal media track, "
            "using a library called MediaInfo.<br>"
            "For <b>image files</b>, it reads the <i>DateTimeOriginal</i> "
            "field from EXIF data (the same metadata your phone camera writes), "
            "falling back to DateTimeDigitized or DateTime if the first is absent.<br><br>"

            "<b>What does null mean?</b><br>"
            "A file is marked <b style='color: #E65100;'>null</b> (shown in orange) "
            "when no embedded media creation date could be found anywhere in the file. "
            "This is common with files that were re-encoded, downloaded from certain "
            "platforms, or created by software that does not write metadata dates.<br><br>"

            "Null files will be renamed with the literal text <i>[null]</i> in place "
            "of the date. You can:<br>"
            "• Use <b>Deselect Null</b> to exclude them from this rename batch<br>"
            "• Use <b>Manual Re-date</b> to assign a date to them yourself"
        )
        layout.addWidget(text)

        tldr = QLabel(
            "<b>TL;DR —</b> Orange files have no date we could read. "
            "If you don't know or don't care, just leave them check-listed and proceed. "
            "If you know when the content was made, you can run it once with Null deselected, "
            "then use <b>Manual Re-date</b> on the orange ones afterward."
        )
        tldr.setWordWrap(True)
        tldr.setFont(QFont('Segoe UI', 9))
        tldr.setStyleSheet(
            'background: #FFF8E1; border: 1px solid #FFE082; '
            'border-radius: 4px; padding: 8px;'
        )
        layout.addWidget(tldr)

        close_btn = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok)
        close_btn.accepted.connect(dlg.accept)
        layout.addWidget(close_btn)

        dlg.exec()

    def _manual_redate(self):
        import re as _re

        selected = [i for i, cb in enumerate(getattr(self, '_checkboxes', []))
                    if cb.isChecked()]
        if not selected:
            QMessageBox.information(self, 'Nothing Selected',
                                    'Select the files you want to re-date first.')
            return

        # Input dialog
        dlg = QDialog(self)
        dlg.setWindowTitle('Manual Re-date')
        dlg.setFixedWidth(340)
        layout = QVBoxLayout(dlg)
        layout.setContentsMargins(16, 14, 16, 12)
        layout.setSpacing(8)

        layout.addWidget(QLabel(f'Assign a date to {len(selected)} selected file(s):'))
        date_edit = QLineEdit()
        date_edit.setPlaceholderText('YYYY-MM-DD')
        date_edit.setFont(QFont('Consolas', 10))
        layout.addWidget(date_edit)

        hint = QLabel('Example: 2024-06-15')
        hint.setFont(QFont('Segoe UI', 8))
        hint.setStyleSheet('color: #888;')
        layout.addWidget(hint)

        btns = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        btns.accepted.connect(dlg.accept)
        btns.rejected.connect(dlg.reject)
        layout.addWidget(btns)

        if dlg.exec() != QDialog.DialogCode.Accepted:
            return

        date_str = date_edit.text().strip()
        if not _re.fullmatch(r'\d{4}-\d{2}-\d{2}', date_str):
            QMessageBox.warning(self, 'Invalid Date',
                                'Date must be in YYYY-MM-DD format.\nExample: 2024-06-15')
            return

        # Rebuild new_name for each selected row using the new date
        from core.renamer import build_new_name
        creator_jp = self._creator_jp_edit.text().strip()
        post_title = self._post_title_edit.text().strip()
        effective_category = self._category_edit.text().strip() or self._category
        null_color = QColor('#FF8C00')

        for i in selected:
            item = self._plan[i]
            new_name = build_new_name(
                self._creator, creator_jp, date_str, post_title,
                item['subfolder_parts'], item['original_stem'],
                effective_category, item['ext'], self._preset
            )
            item['new_name'] = new_name
            item['new_path'] = os.path.join(item['target_dir'], new_name)
            item['is_null'] = False

            # Update table row — clear orange, update new_name cell
            old_cell = self._table.item(i, 1)
            new_cell = self._table.item(i, 2)
            if old_cell:
                old_cell.setForeground(self._table.palette().text().color())
            if new_cell:
                new_cell.setText(new_name)
                new_cell.setForeground(self._table.palette().text().color())

    def _on_confirm(self):
        # Rebuild plan with current optional field values + category override
        creator_jp = self._creator_jp_edit.text().strip()
        post_title = self._post_title_edit.text().strip()
        effective_category = self._category_edit.text().strip() or self._category

        # Re-scan with updated values if anything changed
        if (creator_jp or post_title
                or effective_category != self._category):
            from core.renamer import build_rename_plan
            try:
                self._plan = build_rename_plan(
                    self._folder_path, self._creator, creator_jp,
                    post_title, effective_category, self._preset
                )
                # Re-populate with preserved selections
                old_checked = {i for i, cb in enumerate(self._checkboxes)
                               if cb.isChecked()}
                self._populate_table()
                for i, cb in enumerate(self._checkboxes):
                    cb.setChecked(i in old_checked)
            except Exception as e:
                QMessageBox.critical(self, 'Error', str(e))
                return

        selected = [i for i, cb in enumerate(self._checkboxes) if cb.isChecked()]
        if not selected:
            QMessageBox.information(self, 'Nothing Selected',
                                    'No files are selected for renaming.')
            return

        from core.renamer import apply_rename_plan
        renamed, errors = apply_rename_plan(self._plan, selected)
        self.close()

        if errors:
            QMessageBox.warning(
                None, 'Rename Errors',
                f'Renamed {renamed} file(s). Errors:\n' + '\n'.join(errors)
            )


# ── Helpers ───────────────────────────────────────────────────────────────────

def _bold_label(text: str) -> QLabel:
    lbl = QLabel(text)
    lbl.setFont(QFont('Segoe UI', 9, QFont.Weight.Bold))
    return lbl
