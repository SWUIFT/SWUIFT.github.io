from __future__ import annotations
from datetime import datetime
from enum import Enum, auto
from typing import Any
from PySide6.QtCore import QDateTime, Qt, Signal
from PySide6.QtGui import QDoubleValidator
from PySide6.QtWidgets import QCheckBox, QDateTimeEdit, QDoubleSpinBox, QHBoxLayout, QLabel, QLineEdit, QSpinBox, QWidget
_DT_FORMAT = 'yyyy-MM-dd HH:mm'

class ParamType(Enum):
    INT = auto()
    FLOAT = auto()
    SCIENTIFIC = auto()
    DATETIME = auto()
    BOOL = auto()

class ParamRow(QWidget):
    value_changed = Signal(object)

    def __init__(self, label: str, param_type: ParamType, default: Any=0, tooltip: str='', min_val: float | int | None=None, max_val: float | int | None=None, step: float | int | None=None, suffix: str='', decimals: int=6, label_width: int=240, parent: QWidget | None=None) -> None:
        super().__init__(parent)
        self._type = param_type
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        lbl = QLabel(label)
        lbl.setMinimumWidth(label_width)
        lbl.setWordWrap(False)
        if tooltip:
            lbl.setToolTip(tooltip)
        layout.addWidget(lbl)
        self._widget: QWidget
        if param_type == ParamType.INT:
            w = QSpinBox()
            w.setMinimum(int(min_val) if min_val is not None else 0)
            w.setMaximum(int(max_val) if max_val is not None else 2147483647)
            if step is not None:
                w.setSingleStep(int(step))
            if suffix:
                w.setSuffix(f' {suffix}')
            w.setValue(int(default))
            w.valueChanged.connect(lambda v: self.value_changed.emit(v))
            self._widget = w
        elif param_type == ParamType.FLOAT:
            w = QDoubleSpinBox()
            w.setDecimals(decimals)
            w.setMinimum(float(min_val) if min_val is not None else 0.0)
            w.setMaximum(float(max_val) if max_val is not None else 1000000000000.0)
            if step is not None:
                w.setSingleStep(float(step))
            if suffix:
                w.setSuffix(f' {suffix}')
            w.setValue(float(default))
            w.valueChanged.connect(lambda v: self.value_changed.emit(v))
            self._widget = w
        elif param_type == ParamType.SCIENTIFIC:
            w = QLineEdit()
            w.setValidator(QDoubleValidator())
            w.setText(str(default))
            w.textChanged.connect(lambda t: self.value_changed.emit(t))
            self._widget = w
        elif param_type == ParamType.DATETIME:
            w = QDateTimeEdit()
            w.setDisplayFormat(_DT_FORMAT)
            w.setCalendarPopup(True)
            if isinstance(default, datetime):
                qdt = QDateTime(default.year, default.month, default.day, default.hour, default.minute, 0)
                w.setDateTime(qdt)
            w.dateTimeChanged.connect(lambda _: self.value_changed.emit(self.value()))
            self._widget = w
        elif param_type == ParamType.BOOL:
            w = QCheckBox()
            w.setChecked(bool(default))
            w.checkStateChanged.connect(lambda _: self.value_changed.emit(w.isChecked()))
            self._widget = w
        else:
            raise ValueError(f'Unknown ParamType: {param_type}')
        if tooltip:
            self._widget.setToolTip(tooltip)
        layout.addWidget(self._widget)
        layout.addStretch()

    def value(self) -> Any:
        t = self._type
        if t == ParamType.INT:
            return self._widget.value()
        if t == ParamType.FLOAT:
            return self._widget.value()
        if t == ParamType.SCIENTIFIC:
            try:
                return float(self._widget.text())
            except ValueError:
                return 0.0
        if t == ParamType.DATETIME:
            qdt = self._widget.dateTime()
            d = qdt.date()
            tm = qdt.time()
            return datetime(d.year(), d.month(), d.day(), tm.hour(), tm.minute())
        if t == ParamType.BOOL:
            return self._widget.isChecked()
        return None

    def set_value(self, v: Any) -> None:
        t = self._type
        if t in (ParamType.INT, ParamType.FLOAT):
            self._widget.setValue(v)
        elif t == ParamType.SCIENTIFIC:
            self._widget.setText(str(v))
        elif t == ParamType.DATETIME:
            if isinstance(v, datetime):
                qdt = QDateTime(v.year, v.month, v.day, v.hour, v.minute, 0)
                self._widget.setDateTime(qdt)
        elif t == ParamType.BOOL:
            self._widget.setChecked(bool(v))
