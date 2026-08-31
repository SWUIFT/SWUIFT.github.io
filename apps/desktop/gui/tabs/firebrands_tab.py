from __future__ import annotations
from PySide6.QtWidgets import QPushButton, QVBoxLayout, QWidget
from ..widgets.param_row import ParamRow, ParamType

class FirebrandsTab(QWidget):

    def __init__(self, parent: QWidget | None=None) -> None:
        super().__init__(parent)
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)
        self._fb_wind_coef = ParamRow('Wind Coefficient', ParamType.FLOAT, default=30.0, tooltip='Scales the wind-driven component of firebrand transport distance. Higher values push brands farther downwind.', min_val=0.0, max_val=1000.0, step=0.5, decimals=2)
        self._fb_wind_sd = ParamRow('Wind Std Dev (longitudinal)', ParamType.FLOAT, default=0.3, tooltip='Standard deviation applied to the along-wind component of brand transport, adding stochastic scatter in the wind direction.', min_val=0.0, max_val=100.0, step=0.01, decimals=4)
        self._fb_wind_sd_transverse = ParamRow('Wind Std Dev (transverse)', ParamType.FLOAT, default=4.85, tooltip='Standard deviation applied to the cross-wind component of brand transport. Controls lateral (sideways) spread.', min_val=0.0, max_val=100.0, step=0.05, decimals=4)
        for row in (self._fb_wind_coef, self._fb_wind_sd, self._fb_wind_sd_transverse):
            layout.addWidget(row)
        layout.addStretch()
        reset_btn = QPushButton('Reset to Defaults')
        reset_btn.setFixedWidth(150)
        reset_btn.clicked.connect(self.reset_to_defaults)
        layout.addWidget(reset_btn)

    def get_params(self) -> dict:
        return {'fb_wind_coef': self._fb_wind_coef.value(), 'fb_wind_sd': self._fb_wind_sd.value(), 'fb_wind_sd_transverse': self._fb_wind_sd_transverse.value()}

    def reset_to_defaults(self) -> None:
        self._fb_wind_coef.set_value(30.0)
        self._fb_wind_sd.set_value(0.3)
        self._fb_wind_sd_transverse.set_value(4.85)

    def load_settings(self, data: dict) -> None:
        mapping = {'fb_wind_coef': self._fb_wind_coef, 'fb_wind_sd': self._fb_wind_sd, 'fb_wind_sd_transverse': self._fb_wind_sd_transverse}
        for key, row in mapping.items():
            if key in data:
                row.set_value(data[key])
