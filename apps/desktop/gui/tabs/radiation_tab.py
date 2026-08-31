from __future__ import annotations
from PySide6.QtWidgets import QPushButton, QVBoxLayout, QWidget
from ..widgets.param_row import ParamRow, ParamType

class RadiationTab(QWidget):

    def __init__(self, parent: QWidget | None=None) -> None:
        super().__init__(parent)
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)
        self._rad_energy_ig = ParamRow('Ignition Threshold (W/m²)', ParamType.FLOAT, default=14000.0, tooltip='Minimum radiant flux required to ignite a structure (W/m²). Lower values make structures easier to ignite by radiation.', min_val=0.0, max_val=100000.0, step=100.0, decimals=1)
        self._rad_rf = ParamRow('Radiation Reduction Factor (0–1)', ParamType.FLOAT, default=1.0, tooltip='Scales the computed radiant flux before applying the ignition test. 1.0 = no reduction; values below 1 reduce effective radiation.', min_val=0.0, max_val=1.0, step=0.01, decimals=4)
        for row in (self._rad_energy_ig, self._rad_rf):
            layout.addWidget(row)
        layout.addStretch()
        reset_btn = QPushButton('Reset to Defaults')
        reset_btn.setFixedWidth(150)
        reset_btn.clicked.connect(self.reset_to_defaults)
        layout.addWidget(reset_btn)

    def get_params(self) -> dict:
        return {'rad_energy_ig': self._rad_energy_ig.value(), 'rad_rf': self._rad_rf.value()}

    def reset_to_defaults(self) -> None:
        self._rad_energy_ig.set_value(14000.0)
        self._rad_rf.set_value(1.0)

    def load_settings(self, data: dict) -> None:
        if 'rad_energy_ig' in data:
            self._rad_energy_ig.set_value(data['rad_energy_ig'])
        if 'rad_rf' in data:
            self._rad_rf.set_value(data['rad_rf'])
