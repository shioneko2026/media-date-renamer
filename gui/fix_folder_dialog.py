"""
gui/fix_folder_dialog.py — Dialog shown when a folder name doesn't match the expected format.
Used by all three context-menu launchers.
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QRadioButton, QButtonGroup, QPushButton, QFrame, QMessageBox
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont


class FixFolderDialog(QDialog):
    """
    Modal dialog to gather missing folder metadata (creator, category, status).

    Optional: date_str may be pre-filled (used by update_folder_latest.py).
    On accept, call result_values() to get (creator, date_str, category, status_or_None).
    """

    def __init__(self, folder_name: str, date_str: str = '',
                 latest_file: str = '', parent=None):
        super().__init__(parent)
        self._folder_name = folder_name
        self._result = None

        self.setWindowTitle('Fix Folder Name')
        self.setMinimumWidth(520)
        self.setWindowModality(Qt.WindowModality.ApplicationModal)
        self._build_ui(date_str, latest_file)

    # ── Build ─────────────────────────────────────────────────────────────────

    def _build_ui(self, date_str: str, latest_file: str):
        layout = QVBoxLayout(self)
        layout.setSpacing(8)
        layout.setContentsMargins(16, 14, 16, 12)

        # Header
        header = QLabel(
            "Folder name doesn't match the expected format.\n"
            "Fill in the missing details to fix it:"
        )
        header.setFont(QFont('Segoe UI', 9))
        layout.addWidget(header)

        layout.addWidget(_separator())

        # Creator
        self._creator_edit = QLineEdit(self._folder_name)
        layout.addLayout(_row('Creator Name:', self._creator_edit))

        # Date (only shown when a date is provided — i.e. from latest-date flow)
        self._date_edit = QLineEdit(date_str)
        if date_str:
            date_row = _row('Date:', self._date_edit)
            if latest_file:
                note = QLabel(f'From file: {latest_file}')
                note.setFont(QFont('Consolas', 8))
                note.setStyleSheet('color: #777;')
                note.setWordWrap(True)
            layout.addLayout(date_row)
            if latest_file:
                layout.addWidget(note)

        # Category / Source
        self._category_edit = QLineEdit()
        self._category_edit.setPlaceholderText('e.g. Fanbox, Fanbox, Iwara, Twitter …')
        layout.addLayout(_row('Category:', self._category_edit))

        # Status radio buttons
        status_row = QHBoxLayout()
        status_lbl = QLabel('Status:')
        status_lbl.setFont(QFont('Segoe UI', 9, QFont.Weight.Bold))
        status_lbl.setFixedWidth(110)
        status_row.addWidget(status_lbl)

        self._status_group = QButtonGroup(self)
        self._status_none = QRadioButton('None')
        self._status_none.setChecked(True)
        self._status_obtained = QRadioButton('[Obtained]')
        self._status_partial = QRadioButton('[Partial]')
        self._status_uncertain = QRadioButton('[Uncertain]')
        for rb in (self._status_none, self._status_obtained,
                   self._status_partial, self._status_uncertain):
            self._status_group.addButton(rb)
            status_row.addWidget(rb)
        status_row.addStretch()
        layout.addLayout(status_row)

        # Live preview
        layout.addWidget(_separator())
        self._preview_lbl = QLabel('Preview: ')
        self._preview_lbl.setFont(QFont('Consolas', 8))
        self._preview_lbl.setStyleSheet('color: #888;')
        self._preview_lbl.setWordWrap(True)
        layout.addWidget(self._preview_lbl)

        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        cancel_btn = QPushButton('Cancel')
        cancel_btn.setFixedWidth(100)
        cancel_btn.clicked.connect(self.reject)
        confirm_btn = QPushButton('Confirm')
        confirm_btn.setFixedWidth(100)
        confirm_btn.setDefault(True)
        confirm_btn.setStyleSheet('background-color: #4CAF50; color: white; font-weight: bold;')
        confirm_btn.clicked.connect(self._on_confirm)
        btn_layout.addWidget(cancel_btn)
        btn_layout.addWidget(confirm_btn)
        layout.addLayout(btn_layout)

        # Wire live preview
        self._creator_edit.textChanged.connect(self._update_preview)
        self._date_edit.textChanged.connect(self._update_preview)
        self._category_edit.textChanged.connect(self._update_preview)
        self._status_group.buttonToggled.connect(self._update_preview)
        self._update_preview()

        self._category_edit.setFocus()

    # ── Slots ─────────────────────────────────────────────────────────────────

    def _update_preview(self, *_):
        from core.folder import build_folder_name
        from core.config import get_active_preset, load_config

        creator = self._creator_edit.text().strip() or self._folder_name
        date = self._date_edit.text().strip() or 'YYYY-MM-DD'
        category = self._category_edit.text().strip() or '?'
        status = self._get_status()

        try:
            preset = get_active_preset(load_config())
            name = build_folder_name(creator, date, category, status, preset)
        except Exception:
            name = f'{creator} [{date}] [{category}]'
            if status:
                name += f' [{status}]'

        self._preview_lbl.setText(f'Preview: {name}')

    def _on_confirm(self):
        if not self._category_edit.text().strip():
            QMessageBox.warning(self, 'Missing Category',
                                'Please enter a Category/Source.')
            return
        self._result = (
            self._creator_edit.text().strip() or self._folder_name,
            self._date_edit.text().strip(),
            self._category_edit.text().strip(),
            self._get_status(),
        )
        self.accept()

    def _get_status(self):
        if self._status_obtained.isChecked():
            return 'Obtained'
        if self._status_partial.isChecked():
            return 'Partial'
        if self._status_uncertain.isChecked():
            return 'Uncertain'
        return None

    # ── Public ────────────────────────────────────────────────────────────────

    def result_values(self):
        """Returns (creator, date_str, category, status_or_None) after accept()."""
        return self._result


# ── Helpers ───────────────────────────────────────────────────────────────────

def _row(label_text: str, widget) -> QHBoxLayout:
    row = QHBoxLayout()
    lbl = QLabel(label_text)
    lbl.setFont(QFont('Segoe UI', 9, QFont.Weight.Bold))
    lbl.setFixedWidth(110)
    row.addWidget(lbl)
    row.addWidget(widget)
    return row


def _separator() -> QFrame:
    line = QFrame()
    line.setFrameShape(QFrame.Shape.HLine)
    line.setStyleSheet('color: #ddd;')
    return line
