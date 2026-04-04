"""
gui/confirm_dialog.py — Shared confirmation dialog for folder update operations.
Used by update_folder_today.py and update_folder_latest.py.
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QFrame
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont


class ConfirmFolderRenameDialog(QDialog):
    """
    Shows current → proposed folder name, lets user override date, then confirm.

    Args:
        creator:    Creator name string
        date_str:   Proposed date string (YYYY-MM-DD)
        category:   Category/source tag
        status:     Optional status tag string or None
        date_label: Short description of where the date came from
        latest_file: Optional filename that contributed the date
        preset:     Active preset dict (for building preview)
    """

    def __init__(self, creator: str, date_str: str, category: str,
                 status, date_label: str = '',
                 latest_file: str = '', preset: dict = None, parent=None):
        super().__init__(parent)
        self._creator = creator
        self._category = category
        self._status = status
        self._preset = preset or {}
        self._confirmed_date = None

        self.setWindowTitle('Confirm Folder Rename')
        self.setMinimumWidth(500)
        self.setWindowModality(Qt.WindowModality.ApplicationModal)
        self._build_ui(date_str, date_label, latest_file)

    def _build_ui(self, date_str: str, date_label: str, latest_file: str):
        layout = QVBoxLayout(self)
        layout.setSpacing(8)
        layout.setContentsMargins(16, 14, 16, 12)

        header = QLabel('Confirm the folder rename. You can override the date if needed:')
        header.setFont(QFont('Segoe UI', 9))
        layout.addWidget(header)

        layout.addWidget(_separator())

        # Date row
        date_row = QHBoxLayout()
        date_lbl = QLabel('Date:')
        date_lbl.setFont(QFont('Segoe UI', 9, QFont.Weight.Bold))
        date_lbl.setFixedWidth(80)
        date_row.addWidget(date_lbl)

        self._date_edit = QLineEdit(date_str)
        self._date_edit.setFixedWidth(110)
        date_row.addWidget(self._date_edit)

        if date_label:
            note = QLabel(f'  ({date_label})')
            note.setFont(QFont('Segoe UI', 9))
            note.setStyleSheet('color: #666;')
            date_row.addWidget(note)
        date_row.addStretch()
        layout.addLayout(date_row)

        if latest_file:
            file_row = QHBoxLayout()
            fl_lbl = QLabel('From file:')
            fl_lbl.setFont(QFont('Segoe UI', 9, QFont.Weight.Bold))
            fl_lbl.setFixedWidth(80)
            fl_val = QLabel(latest_file)
            fl_val.setFont(QFont('Consolas', 8))
            fl_val.setStyleSheet('color: #555;')
            fl_val.setWordWrap(True)
            file_row.addWidget(fl_lbl)
            file_row.addWidget(fl_val)
            layout.addLayout(file_row)

        layout.addWidget(_separator())

        self._preview_lbl = QLabel()
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

        self._date_edit.textChanged.connect(self._update_preview)
        self._update_preview()

    def _update_preview(self, *_):
        from core.folder import build_folder_name
        date = self._date_edit.text().strip() or 'YYYY-MM-DD'
        try:
            name = build_folder_name(self._creator, date, self._category,
                                     self._status, self._preset)
        except Exception:
            name = f'{self._creator} [{date}] [{self._category}]'
        self._preview_lbl.setText(f'Preview: {name}')

    def _on_confirm(self):
        self._confirmed_date = self._date_edit.text().strip()
        self.accept()

    def confirmed_date(self) -> str:
        """Return the final date string chosen by the user."""
        return self._confirmed_date or ''


# ── Helpers ───────────────────────────────────────────────────────────────────

def _separator() -> QFrame:
    line = QFrame()
    line.setFrameShape(QFrame.Shape.HLine)
    line.setStyleSheet('color: #ddd;')
    return line
