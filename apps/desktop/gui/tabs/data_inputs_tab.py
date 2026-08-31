from __future__ import annotations
import hashlib
import json
import os
from PySide6.QtCore import Signal, Qt
from PySide6.QtWidgets import QFormLayout, QGroupBox, QLabel, QPushButton, QRadioButton, QScrollArea, QVBoxLayout, QWidget
from ..widgets.file_picker import FilePicker, PickMode

class DataInputsTab(QWidget):
    quick_start_requested = Signal(dict)
    _ENTRIES = [('wildland_fire_matrix', 'Wildland Fire Matrix', 'wildland_fire_matrix.mat — known ignition / fire progression → knownig_mat'), ('domain_matrix', 'Domain Matrix', 'domain_matrix.mat — domain classification raster → domains_mat'), ('binary_cover', 'Binary Cover', 'binary_cover_landcover.mat — vegetation vs structure raster → binary_cover'), ('homes_matrix', 'Homes Matrix', 'homes_matrix.mat — building ID raster → homes_mat'), ('latitude', 'Latitude', 'latitude.mat — 1-D latitude vector (length = rows)'), ('longitude', 'Longitude', 'longitude.mat — 1-D longitude vector (length = cols)'), ('radiation_matrix', 'Radiation Matrix', 'radiation_matrix.mat — per-cell radiation hardening → hardening_mat_rad'), ('spotting_matrix', 'Spotting Matrix', 'spotting_matrix.mat — per-cell spotting hardening → hardening_mat_spo'), ('water_matrix', 'Water Matrix (optional)', 'Optional water_matrix.mat — non-burnable water cells; blank means no cells are marked as water'), ('wind_file', 'Wind File', 'wind.mat — HDF5/v7.3 file containing wind_s and wind_d arrays')]

    def __init__(self, app_dir: str, parent: QWidget | None=None) -> None:
        super().__init__(parent)
        self._app_dir = app_dir
        self._build_ui()

    def _build_ui(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(12, 12, 12, 12)
        outer.setSpacing(8)
        self._marshall_mode = QRadioButton('Marshall packaged dataset (recommended)')
        self._extracted_mode = QRadioButton('Advanced: select extracted files individually')
        self._marshall_mode.setChecked(True)
        outer.addWidget(self._marshall_mode)
        marshall_box = QGroupBox('Marshall Quick Start')
        marshall_layout = QVBoxLayout(marshall_box)
        marshall_layout.addWidget(QLabel(
            'Choose the folder containing the Marshall dataset. SWUIFT validates '
            'the packaged manifest and local files; it never downloads data automatically.'
        ))
        self._dataset_root = FilePicker(
            label='Dataset Folder',
            default_dir=self._app_dir,
            pick_mode=PickMode.FOLDER,
            placeholder='Select the Marshall folder or its parent …',
        )
        self._dataset_root.path_changed.connect(self._update_summary)
        marshall_layout.addWidget(self._dataset_root)
        self._validation_summary = QLabel('Not validated — choose a local dataset folder.')
        self._validation_summary.setWordWrap(True)
        marshall_layout.addWidget(self._validation_summary)
        quick_start = QPushButton('Validate and Apply Marshall Defaults')
        quick_start.clicked.connect(self._apply_marshall)
        marshall_layout.addWidget(quick_start)
        outer.addWidget(marshall_box)

        self._advanced_box = QGroupBox('Extracted per-file inputs')
        advanced_layout = QVBoxLayout(self._advanced_box)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        inner = QWidget()
        form = QFormLayout(inner)
        form.setSpacing(6)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow)
        self._pickers: dict[str, FilePicker] = {}
        for key, label, tip in self._ENTRIES:
            lbl = QLabel(label)
            lbl.setToolTip(tip)
            picker = FilePicker(label='', file_filter='MAT files (*.mat)', default_dir=self._app_dir, pick_mode=PickMode.FILE, placeholder=f'Select {label} …')
            picker.setToolTip(tip)
            self._pickers[key] = picker
            form.addRow(lbl, picker)
        scroll.setWidget(inner)
        advanced_layout.addWidget(scroll)
        outer.addWidget(self._extracted_mode)
        outer.addWidget(self._advanced_box, stretch=1)
        reset_btn = QPushButton('Reset to Defaults')
        reset_btn.setFixedWidth(150)
        reset_btn.clicked.connect(self.reset_to_defaults)
        outer.addWidget(reset_btn)
        self._marshall_mode.toggled.connect(self._sync_mode)
        self._extracted_mode.toggled.connect(self._sync_mode)
        self._sync_mode()

    def get_data_params(self) -> dict:
        if self._marshall_mode.isChecked():
            return {
                'mode': 'scenario',
                'scenario_id': 'marshall',
                'data_root': self._dataset_root.path(),
            }
        params: dict = {'mode': 'extracted'}
        for key, picker in self._pickers.items():
            value = picker.path()
            params[key] = value.strip() if key == 'water_matrix' else value
        return params

    def validate(self) -> tuple[bool, str]:
        if self._marshall_mode.isChecked():
            return self._validate_marshall()
        missing = []
        for key, picker in self._pickers.items():
            p = picker.path().strip()
            if key == 'water_matrix' and not p:
                continue
            if not p or not os.path.isfile(p):
                label = key.replace('_', ' ').title()
                missing.append(label)
        if missing:
            return (False, 'Missing or invalid files:\n• ' + '\n• '.join(missing))
        return (True, '')

    def _validate_marshall(self) -> tuple[bool, str]:
        root = self._dataset_root.path()
        if not root or not os.path.isdir(root):
            return False, 'Choose an existing folder containing the Marshall dataset.'
        try:
            from swuift.scenario import load_scenario_manifest

            manifest = load_scenario_manifest('marshall')
            resolved = manifest.validate_data_files(root)
            dataset_manifest_path = resolved / 'manifest.json'
            if not dataset_manifest_path.is_file():
                raise FileNotFoundError(
                    'The official manifest.json is missing. Extract the complete '
                    'Marshall example archive before selecting its folder.'
                )
            dataset_payload = json.loads(dataset_manifest_path.read_text(encoding='utf-8'))
            dataset_manifest = load_scenario_manifest(dataset_manifest_path)
            if dataset_manifest.config != manifest.config:
                raise ValueError('The dataset configuration does not match this SWUIFT release.')
            artifacts = dataset_payload.get('artifacts')
            if not isinstance(artifacts, dict):
                raise ValueError('manifest.json does not contain an artifacts checksum map.')
            for name in manifest.required_input_files():
                expected = artifacts.get(name, {}).get('sha256')
                if not expected:
                    raise ValueError(f'manifest.json has no SHA-256 value for {name}.')
                digest = hashlib.sha256()
                with (resolved / name).open('rb') as handle:
                    for block in iter(lambda: handle.read(8 * 1024 * 1024), b''):
                        digest.update(block)
                if digest.hexdigest() != expected:
                    raise ValueError(f'SHA-256 verification failed for {name}.')
        except Exception as exc:
            self._validation_summary.setText(f'Invalid Marshall dataset:\n{exc}')
            self._validation_summary.setStyleSheet('color: #b00020;')
            return False, str(exc)
        count = len(manifest.required_input_files())
        self._validation_summary.setText(
            f'Valid Marshall dataset ✓  {count} files and SHA-256 hashes verified\n'
            f'Resolved folder: {resolved}'
        )
        self._validation_summary.setStyleSheet('color: #16733a;')
        return True, ''

    def _apply_marshall(self) -> None:
        ok, message = self._validate_marshall()
        if not ok:
            self._validation_summary.setToolTip(message)
            return
        from swuift.scenario import load_scenario_manifest

        self.quick_start_requested.emit(load_scenario_manifest('marshall').config)

    def _update_summary(self, *_args) -> None:
        self._validation_summary.setText('Not validated — click “Validate and Apply Marshall Defaults”.')
        self._validation_summary.setStyleSheet('')

    def _sync_mode(self, *_args) -> None:
        scenario = self._marshall_mode.isChecked()
        self._dataset_root.setEnabled(scenario)
        self._advanced_box.setEnabled(not scenario)

    def reset_to_defaults(self) -> None:
        self._marshall_mode.setChecked(True)
        self._dataset_root.set_path('')
        for picker in self._pickers.values():
            picker.set_path('')

    def load_settings(self, data: dict) -> None:
        mode = data.get('mode', 'extracted')
        self._marshall_mode.setChecked(mode == 'scenario')
        self._extracted_mode.setChecked(mode != 'scenario')
        if 'data_root' in data:
            self._dataset_root.set_path(data['data_root'])
        for key, picker in self._pickers.items():
            if key in data:
                picker.set_path(data[key])
