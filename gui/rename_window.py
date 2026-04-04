"""
gui/rename_window.py — Main PyQt6 rename preview window.
Replaces the tkinter PreviewWindow in the old rename_media.py.
"""

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QTableWidget, QTableWidgetItem, QHeaderView,
    QPushButton, QProgressBar, QMessageBox, QCheckBox, QAbstractItemView
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
        self._select_all_btn.setFixedWidth(100)
        self._select_all_btn.clicked.connect(self._select_all)
        self._deselect_all_btn = QPushButton('Deselect All')
        self._deselect_all_btn.setFixedWidth(100)
        self._deselect_all_btn.clicked.connect(self._deselect_all)
        btn_row.addWidget(self._select_all_btn)
        btn_row.addWidget(self._deselect_all_btn)
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
