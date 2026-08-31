from __future__ import annotations
import os
from PySide6.QtCore import QStandardPaths, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QLabel, QPushButton, QVBoxLayout, QWidget
from ..widgets.file_picker import FilePicker, PickMode
from ..widgets.param_row import ParamRow, ParamType

class OutputTab(QWidget):

    def __init__(self, app_dir: str, parent: QWidget | None=None) -> None:
        super().__init__(parent)
        self._app_dir = app_dir
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)
        default_output = self.default_output_dir()
        self._output_dir = FilePicker(label='Output Folder', default_dir=default_output, pick_mode=PickMode.FOLDER, placeholder='Select output folder …')
        self._output_dir.set_path(default_output)
        layout.addWidget(self._output_dir)
        warning = QLabel('Resource note: Marshall is a large simulation. Lazy Wind uses much less memory but runs more slowly; preloading can require about 7 GB of additional RAM.')
        warning.setWordWrap(True)
        warning.setStyleSheet('color: #8a5700;')
        layout.addWidget(warning)
        self._make_video = ParamRow('Generate Video / GIF', ParamType.BOOL, default=True, tooltip='When checked, assembles frames into simulation.mp4 and simulation.gif after the run completes. The desktop app includes the required encoders.')
        self._dpi_hires = ParamRow('Frame DPI', ParamType.INT, default=600, tooltip='DPI for rendered PNG frames and the output video.', min_val=72, max_val=1200, step=50)
        self._dump_interval = ParamRow('Dump Interval (0 = off)', ParamType.INT, default=0, tooltip='Save full per-step state arrays every N timesteps. 0 = disabled. Useful for debugging or verification.', min_val=0, max_val=10000)
        self._dump_csv = ParamRow('Dump as CSV', ParamType.BOOL, default=False, tooltip='When per-step dumps are enabled, use CSV format instead of binary .npy. CSV is portable but significantly slower.')
        self._lazy_wind = ParamRow('Lazy Wind (low RAM mode)', ParamType.BOOL, default=False, tooltip='When checked, wind slices are read from disk on demand instead of preloaded into RAM. Saves ~7 GB but is much slower per step.')
        self._dump_radiation_csv = ParamRow('Export radiation flux CSV per frame', ParamType.BOOL, default=False, tooltip='Save the per-cell radiation flux matrix (radtotal) as a CSV file for each timestep into a radiation_csv/ subdirectory.')
        self._dump_spotting_csv = ParamRow('Export spotting (brands) CSV per frame', ParamType.BOOL, default=False, tooltip='Save the per-cell brand generation count matrix as a CSV file for each timestep into a spotting_csv/ subdirectory.')
        for row in (self._make_video, self._dpi_hires, self._dump_interval, self._dump_csv, self._lazy_wind, self._dump_radiation_csv, self._dump_spotting_csv):
            layout.addWidget(row)
        layout.addStretch()
        reset_btn = QPushButton('Reset to Defaults')
        reset_btn.setFixedWidth(150)
        reset_btn.clicked.connect(self.reset_to_defaults)
        layout.addWidget(reset_btn)
        open_btn = QPushButton('Open Output Folder')
        open_btn.setFixedWidth(150)
        open_btn.clicked.connect(self.open_output_folder)
        layout.addWidget(open_btn)

    @staticmethod
    def default_output_dir() -> str:
        base = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.DocumentsLocation)
        if not base:
            base = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppDataLocation)
        return os.path.join(base or os.path.expanduser('~'), 'SWUIFT Outputs')

    def get_params(self) -> dict:
        return {'output_dir': self._output_dir.path() or self.default_output_dir(), 'make_video': self._make_video.value(), 'dpi_hires': self._dpi_hires.value(), 'dump_interval': self._dump_interval.value(), 'dump_csv': self._dump_csv.value(), 'lazy_wind': self._lazy_wind.value(), 'dump_radiation_csv': self._dump_radiation_csv.value(), 'dump_spotting_csv': self._dump_spotting_csv.value()}

    def reset_to_defaults(self) -> None:
        self._output_dir.set_path(self.default_output_dir())
        self._make_video.set_value(True)
        self._dpi_hires.set_value(600)
        self._dump_interval.set_value(0)
        self._dump_csv.set_value(False)
        self._lazy_wind.set_value(False)
        self._dump_radiation_csv.set_value(False)
        self._dump_spotting_csv.set_value(False)

    def load_settings(self, data: dict) -> None:
        if 'output_dir' in data:
            self._output_dir.set_path(data['output_dir'])
        mapping = {'make_video': self._make_video, 'dpi_hires': self._dpi_hires, 'dump_interval': self._dump_interval, 'dump_csv': self._dump_csv, 'lazy_wind': self._lazy_wind, 'dump_radiation_csv': self._dump_radiation_csv, 'dump_spotting_csv': self._dump_spotting_csv}
        for key, row in mapping.items():
            if key in data:
                row.set_value(data[key])

    def set_marshall_defaults(self) -> None:
        self._lazy_wind.set_value(True)
        self._dpi_hires.set_value(150)

    def open_output_folder(self) -> bool:
        path = self.get_params()['output_dir']
        os.makedirs(path, exist_ok=True)
        return QDesktopServices.openUrl(QUrl.fromLocalFile(path))
