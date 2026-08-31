from __future__ import annotations

from datetime import datetime

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QComboBox, QLabel, QPushButton, QVBoxLayout, QWidget
from swuift.timezones import local_to_utc, timezone_catalog, utc_isoformat

from ..widgets.param_row import ParamRow, ParamType

_T_STEP_MIN: float = 5.0
_T_START = datetime(2025, 1, 7, 18, 20)
_T_END = datetime(2025, 1, 8, 14, 20)
_GRID_SIZE = 10.0

def _calc_steps(t_start: datetime, t_end: datetime, timezone_name: str) -> int:
    start_utc = local_to_utc(t_start, timezone_name)
    end_utc = local_to_utc(t_end, timezone_name)
    delta_seconds = int((end_utc - start_utc).total_seconds())
    if delta_seconds <= 0:
        return 0
    step_seconds = int(_T_STEP_MIN * 60)
    if delta_seconds % step_seconds:
        raise ValueError(
            f'The UTC simulation interval must be divisible by {_T_STEP_MIN:g} minutes.'
        )
    return delta_seconds // step_seconds + 1

class GridTimeTab(QWidget):

    def __init__(self, parent: QWidget | None=None) -> None:
        super().__init__(parent)
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)
        self._t_start = ParamRow('Simulation Start', ParamType.DATETIME, default=_T_START, tooltip='Date and time when the simulation begins.')
        self._t_end = ParamRow('Simulation End', ParamType.DATETIME, default=_T_END, tooltip='Date and time when the simulation ends.')
        self._grid_size = ParamRow('Grid Size (m)', ParamType.FLOAT, default=_GRID_SIZE, tooltip='Physical cell size in metres.', min_val=0.001, max_val=10000.0, step=0.125, decimals=3)
        self._timezone_label = QLabel('Simulation Timezone (IANA)')
        self._timezone = QComboBox()
        self._timezone.setEditable(True)
        self._timezone.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        self._timezone.addItems(timezone_catalog())
        self._timezone.setCurrentText('UTC')
        self._timezone.setToolTip(
            'Required IANA timezone. Start and end are entered in this local timezone; '
            'SWUIFT converts them to UTC internally.'
        )
        completer = self._timezone.completer()
        completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        completer.setFilterMode(Qt.MatchFlag.MatchContains)
        self._steps_label = QLabel()
        self._steps_label.setStyleSheet('color: #555; font-style: italic;')
        self._update_steps_label()
        self._t_start.value_changed.connect(self._update_steps_label)
        self._t_end.value_changed.connect(self._update_steps_label)
        self._grid_size.value_changed.connect(self._update_steps_label)
        self._timezone.currentTextChanged.connect(self._update_steps_label)
        for row in (self._t_start, self._t_end, self._grid_size):
            layout.addWidget(row)
        layout.addWidget(self._timezone_label)
        layout.addWidget(self._steps_label)
        layout.addStretch()
        reset_btn = QPushButton('Reset to Defaults')
        reset_btn.setFixedWidth(150)
        reset_btn.clicked.connect(self.reset_to_defaults)
        layout.addWidget(reset_btn)

    def _update_steps_label(self, *_) -> None:
        t_start = self._t_start.value()
        t_end = self._t_end.value()
        timezone_name = self._timezone.currentText().strip()
        try:
            steps = _calc_steps(t_start, t_end, timezone_name)
            start_utc = local_to_utc(t_start, timezone_name)
            end_utc = local_to_utc(t_end, timezone_name)
            delta_h = (end_utc - start_utc).total_seconds() / 3600.0 if steps > 0 else 0.0
        except ValueError as exc:
            self._steps_label.setText(f'⚠  {exc}')
            self._steps_label.setStyleSheet('color: red; font-style: italic;')
            return
        if steps <= 0:
            self._steps_label.setText('⚠  End time must be after start time.')
            self._steps_label.setStyleSheet('color: red; font-style: italic;')
            return
        self._steps_label.setText(
            f'Calculated steps: {steps} ({delta_h:.1f} h · {_T_STEP_MIN:.0f}-min timestep · '
            f'grid = {self._grid_size.value():g} m)\n'
            f'UTC: {utc_isoformat(start_utc)} → {utc_isoformat(end_utc)}'
        )
        self._steps_label.setStyleSheet('color: #555; font-style: italic;')

    def get_params(self) -> dict:
        timezone_name = self._timezone.currentText().strip()
        steps = _calc_steps(self._t_start.value(), self._t_end.value(), timezone_name)
        if steps <= 0:
            raise ValueError('End time must be after start time.')
        return {'t_start': self._t_start.value(), 't_end': self._t_end.value(), 'timezone': timezone_name, 'maxstep': steps, 'grid_size': self._grid_size.value()}

    def reset_to_defaults(self) -> None:
        self._t_start.set_value(_T_START)
        self._t_end.set_value(_T_END)
        self._timezone.setCurrentText('UTC')
        self._grid_size.set_value(_GRID_SIZE)

    def apply_scenario_config(self, config: dict) -> None:
        self._t_start.set_value(datetime.fromisoformat(config['t_start']))
        self._t_end.set_value(datetime.fromisoformat(config['t_end']))
        self._timezone.setCurrentText(str(config['timezone']))
        self._grid_size.set_value(float(config['grid_size']))
        self._update_steps_label()

    def load_settings(self, data: dict) -> None:
        if 't_start' in data:
            v = data['t_start']
            self._t_start.set_value(datetime.fromisoformat(v) if isinstance(v, str) else v)
        if 't_end' in data:
            v = data['t_end']
            self._t_end.set_value(datetime.fromisoformat(v) if isinstance(v, str) else v)
        self._timezone.setCurrentText(str(data.get('timezone', '')))
        if 'grid_size' in data:
            self._grid_size.set_value(data['grid_size'])
