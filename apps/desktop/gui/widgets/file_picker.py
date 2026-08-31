from __future__ import annotations
import os
from enum import Enum, auto
from PySide6.QtCore import Signal
from PySide6.QtWidgets import QFileDialog, QHBoxLayout, QLabel, QLineEdit, QPushButton, QSizePolicy, QWidget

class PickMode(Enum):
    FILE = auto()
    FOLDER = auto()

class FilePicker(QWidget):
    path_changed = Signal(str)

    def __init__(self, label: str='', file_filter: str='All files (*)', default_dir: str='', pick_mode: PickMode=PickMode.FILE, placeholder: str='', parent: QWidget | None=None) -> None:
        super().__init__(parent)
        self._filter = file_filter
        self._default_dir = default_dir or os.path.expanduser('~')
        self._mode = pick_mode
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        if label:
            lbl = QLabel(label)
            lbl.setMinimumWidth(180)
            lbl.setWordWrap(False)
            layout.addWidget(lbl)
        self._edit = QLineEdit()
        self._edit.setPlaceholderText(placeholder or '')
        self._edit.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self._edit.textChanged.connect(self.path_changed)
        layout.addWidget(self._edit)
        self._btn = QPushButton('Browse…')
        self._btn.setFixedWidth(80)
        self._btn.clicked.connect(self._browse)
        layout.addWidget(self._btn)

    def path(self) -> str:
        return self._edit.text().strip()

    def set_path(self, p: str) -> None:
        self._edit.setText(p)

    def set_default_dir(self, d: str) -> None:
        self._default_dir = d

    def _browse(self) -> None:
        start = self._edit.text().strip() or self._default_dir
        if os.path.isfile(start):
            start = os.path.dirname(start)
        if not os.path.isdir(start):
            start = self._default_dir
        if self._mode == PickMode.FOLDER:
            result = QFileDialog.getExistingDirectory(self, 'Select Folder', start)
            if result:
                self._edit.setText(result)
        else:
            result, _ = QFileDialog.getOpenFileName(self, 'Select File', start, self._filter)
            if result:
                self._edit.setText(result)
