from __future__ import annotations
from PySide6.QtWidgets import QPushButton, QVBoxLayout, QWidget
from ..widgets.param_row import ParamRow, ParamType

class HardeningTab(QWidget):

    def __init__(self, parent: QWidget | None=None) -> None:
        super().__init__(parent)
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)
        self._hardening_rad = ParamRow('Radiation Hardening Level (%)', ParamType.FLOAT, default=70.0, tooltip='Percentage of structures that are radiation-hardened (0–100). Higher values mean more structures resist radiation ignition.', min_val=0.0, max_val=100.0, step=1.0, decimals=1)
        self._hardening_spo = ParamRow('Spotting Hardening Level (%)', ParamType.FLOAT, default=70.0, tooltip='Percentage of structures that are spotting-hardened (0–100). Higher values mean more structures resist firebrand ignition.', min_val=0.0, max_val=100.0, step=1.0, decimals=1)
        self._seed_hardening = ParamRow('Seed — Hardening RNG', ParamType.INT, default=123456, tooltip='Random seed for hardening stochasticity. Use the same value to reproduce runs.', min_val=0, max_val=2147483647)
        self._seed_spread = ParamRow('Seed — Spread RNG', ParamType.INT, default=10, tooltip='Random seed for fire-spread stochasticity. Use the same value to reproduce runs.', min_val=0, max_val=2147483647)
        for row in (self._hardening_rad, self._hardening_spo, self._seed_hardening, self._seed_spread):
            layout.addWidget(row)
        layout.addStretch()
        reset_btn = QPushButton('Reset to Defaults')
        reset_btn.setFixedWidth(150)
        reset_btn.clicked.connect(self.reset_to_defaults)
        layout.addWidget(reset_btn)

    def get_params(self) -> dict:
        return {'hardening_rad': self._hardening_rad.value(), 'hardening_spo': self._hardening_spo.value(), 'seed_hardening': self._seed_hardening.value(), 'seed_spread': self._seed_spread.value()}

    def reset_to_defaults(self) -> None:
        self._hardening_rad.set_value(70.0)
        self._hardening_spo.set_value(70.0)
        self._seed_hardening.set_value(123456)
        self._seed_spread.set_value(10)

    def load_settings(self, data: dict) -> None:
        mapping = {'hardening_rad': self._hardening_rad, 'hardening_spo': self._hardening_spo, 'seed_hardening': self._seed_hardening, 'seed_spread': self._seed_spread}
        for key, row in mapping.items():
            if key in data:
                row.set_value(data[key])
