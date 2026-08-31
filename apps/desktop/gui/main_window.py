from __future__ import annotations

import json
import os

from PySide6.QtCore import QSettings, Qt, QTimer
from PySide6.QtGui import QAction, QIcon
from PySide6.QtWidgets import (
    QApplication,
    QDockWidget,
    QFileDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMainWindow,
    QMenu,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QSplitter,
    QTableView,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from .app import _ICON_PATH, APP_DIR, APP_VERSION, BUILD_ID, RESOURCE_DIR
from .job_queue import (
    _COL_OUTDIR,
    STATUS_DONE,
    STATUS_FAILED,
    STATUS_PENDING,
    STATUS_RUNNING,
    JobConfig,
    JobQueueModel,
)
from .job_runner import JobRunner
from .tabs.data_inputs_tab import DataInputsTab
from .tabs.firebrands_tab import FirebrandsTab
from .tabs.grid_time_tab import GridTimeTab
from .tabs.hardening_tab import HardeningTab
from .tabs.output_tab import OutputTab
from .tabs.radiation_tab import RadiationTab

_ORG = 'SWUIFT'
_APP = 'SWUIFT'

class MainWindow(QMainWindow):

    def __init__(self, parent: QWidget | None=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("SWUIFT - WUI fire spread simulation")
        self.resize(1100, 800)
        if os.path.isfile(_ICON_PATH):
            self.setWindowIcon(QIcon(_ICON_PATH))
        self._runner: JobRunner | None = None
        self._queue_model = JobQueueModel(self)
        self._build_menu()
        self._build_ui()
        self._restore_settings()
        self._tick_timer = QTimer(self)
        self._tick_timer.setInterval(1000)
        self._tick_timer.timeout.connect(self._queue_model.tick)
        self._tick_timer.start()

    def _build_menu(self) -> None:
        menubar = self.menuBar()
        file_menu = menubar.addMenu('&File')
        act_save = QAction('Save Settings as JSON…', self)
        act_save.setShortcut('Ctrl+S')
        act_save.triggered.connect(self._save_settings_json)
        file_menu.addAction(act_save)
        act_load = QAction('Load Settings from JSON…', self)
        act_load.setShortcut('Ctrl+O')
        act_load.triggered.connect(self._load_settings_json)
        file_menu.addAction(act_load)
        file_menu.addSeparator()
        act_quit = QAction('Quit', self)
        act_quit.setShortcut('Ctrl+Q')
        act_quit.triggered.connect(QApplication.quit)
        file_menu.addAction(act_quit)
        help_menu = menubar.addMenu('&Help')
        act_about = QAction('About SWUIFT…', self)
        act_about.triggered.connect(self._show_about)
        help_menu.addAction(act_about)

    def _build_ui(self) -> None:
        splitter = QSplitter(Qt.Orientation.Vertical)
        self.setCentralWidget(splitter)
        self._tabs = QTabWidget()
        self._data_tab = DataInputsTab(APP_DIR)
        self._grid_tab = GridTimeTab()
        self._rad_tab = RadiationTab()
        self._fb_tab = FirebrandsTab()
        self._hard_tab = HardeningTab()
        self._out_tab = OutputTab(APP_DIR)
        self._data_tab.quick_start_requested.connect(self._apply_marshall_defaults)
        self._tabs.addTab(self._data_tab, 'Data Inputs')
        self._tabs.addTab(self._grid_tab, 'Grid & Time')
        self._tabs.addTab(self._rad_tab, 'Radiation')
        self._tabs.addTab(self._fb_tab, 'Firebrands')
        self._tabs.addTab(self._hard_tab, 'Hardening & Seeds')
        self._tabs.addTab(self._out_tab, 'Output Settings')
        splitter.addWidget(self._tabs)
        log_widget = QWidget()
        log_layout = QVBoxLayout(log_widget)
        log_layout.setContentsMargins(4, 4, 4, 4)
        log_header = QHBoxLayout()
        log_header.addWidget(QLabel('Simulation Log'))
        clear_btn = QPushButton('Clear')
        clear_btn.setFixedWidth(60)
        log_header.addWidget(clear_btn)
        log_header.addStretch()
        log_layout.addLayout(log_header)
        self._log = QTextEdit()
        self._log.setReadOnly(True)
        self._log.setFontFamily('Courier New, Menlo, monospace')
        log_layout.addWidget(self._log)
        clear_btn.clicked.connect(self._log.clear)
        splitter.addWidget(log_widget)
        splitter.setSizes([580, 180])
        queue_dock = QDockWidget('Job Queue', self)
        queue_dock.setAllowedAreas(Qt.DockWidgetArea.BottomDockWidgetArea)
        queue_dock.setFeatures(QDockWidget.DockWidgetFeature.DockWidgetMovable | QDockWidget.DockWidgetFeature.DockWidgetFloatable)
        queue_widget = QWidget()
        queue_layout = QVBoxLayout(queue_widget)
        queue_layout.setContentsMargins(6, 6, 6, 6)
        queue_layout.setSpacing(4)
        btn_row = QHBoxLayout()
        self._add_btn = QPushButton('Add to Queue')
        self._run_btn = QPushButton('Run All')
        self._cancel_btn = QPushButton('Cancel')
        self._cancel_btn.setEnabled(False)
        self._remove_btn = QPushButton('Remove Selected')
        self._remove_btn.setToolTip('Remove the currently selected pending job from the queue')
        self._remove_btn.setEnabled(False)
        self._dup_btn = QPushButton('Duplicate Selected')
        self._dup_btn.setToolTip('Add a Pending copy of the selected job at the end of the queue')
        self._dup_btn.setEnabled(False)
        self._clear_btn = QPushButton('Clear Queue')
        self._clear_btn.setToolTip('Remove all jobs from the queue')
        btn_row.addWidget(self._add_btn)
        btn_row.addWidget(self._run_btn)
        btn_row.addWidget(self._cancel_btn)
        btn_row.addSpacing(16)
        btn_row.addWidget(self._remove_btn)
        btn_row.addWidget(self._dup_btn)
        btn_row.addWidget(self._clear_btn)
        btn_row.addStretch()
        queue_layout.addLayout(btn_row)
        self._progress = QProgressBar()
        self._progress.setValue(0)
        self._progress_label = QLabel('Idle')
        prog_row = QHBoxLayout()
        prog_row.addWidget(self._progress_label)
        prog_row.addWidget(self._progress, stretch=1)
        queue_layout.addLayout(prog_row)
        self._queue_view = QTableView()
        self._queue_view.setModel(self._queue_model)
        hdr = self._queue_view.horizontalHeader()
        hdr.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        hdr.setSectionResizeMode(_COL_OUTDIR, QHeaderView.ResizeMode.Stretch)
        self._queue_view.setSelectionBehavior(QTableView.SelectionBehavior.SelectRows)
        self._queue_view.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self._queue_view.customContextMenuRequested.connect(self._queue_context_menu)
        self._queue_view.doubleClicked.connect(self._show_job_detail)
        self._queue_view.selectionModel().selectionChanged.connect(self._on_queue_selection_changed)
        queue_layout.addWidget(self._queue_view)
        queue_dock.setWidget(queue_widget)
        self.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, queue_dock)
        self.resizeDocks([queue_dock], [280], Qt.Orientation.Vertical)
        self._add_btn.clicked.connect(self._add_to_queue)
        self._run_btn.clicked.connect(self._run_all)
        self._cancel_btn.clicked.connect(self._cancel_run)
        self._remove_btn.clicked.connect(self._remove_selected_job)
        self._dup_btn.clicked.connect(self._duplicate_selected_job)
        self._clear_btn.clicked.connect(self._clear_queue)
        self.statusBar().showMessage('Ready.')

    def _add_to_queue(self) -> None:
        ok, msg = self._data_tab.validate()
        if not ok:
            QMessageBox.warning(self, 'Invalid Data Inputs', msg)
            return
        out_params = self._out_tab.get_params()
        if not out_params['lazy_wind']:
            ret = QMessageBox.question(self, 'RAM Usage Warning', "Wind will be preloaded into RAM (~7 GB).\nEnable 'Lazy Wind' in Output Settings to reduce memory usage.\n\nContinue adding this job?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if ret != QMessageBox.StandardButton.Yes:
                return
        data_p = self._data_tab.get_data_params()
        try:
            grid_p = self._grid_tab.get_params()
        except ValueError as exc:
            QMessageBox.warning(self, 'Invalid Simulation Time', str(exc))
            return
        rad_p = self._rad_tab.get_params()
        fb_p = self._fb_tab.get_params()
        hard_p = self._hard_tab.get_params()
        try:
            os.makedirs(out_params['output_dir'], exist_ok=True)
            if not os.access(out_params['output_dir'], os.W_OK):
                raise PermissionError('The selected output folder is not writable.')
        except OSError as exc:
            QMessageBox.warning(self, 'Invalid Output Folder', str(exc))
            return
        scenario = data_p.get('mode') == 'scenario'
        job = JobConfig(data_mode=data_p.get('mode', 'extracted'), scenario_id=data_p.get('scenario_id', '') if scenario else '', data_root=data_p.get('data_root', '') if scenario else '', wildland_fire_matrix=data_p.get('wildland_fire_matrix', ''), domain_matrix=data_p.get('domain_matrix', ''), binary_cover=data_p.get('binary_cover', ''), homes_matrix=data_p.get('homes_matrix', ''), latitude=data_p.get('latitude', ''), longitude=data_p.get('longitude', ''), radiation_matrix=data_p.get('radiation_matrix', ''), spotting_matrix=data_p.get('spotting_matrix', ''), water_matrix=data_p.get('water_matrix', ''), wind_file=data_p.get('wind_file', ''), t_start=grid_p['t_start'], t_end=grid_p['t_end'], timezone=grid_p['timezone'], maxstep=grid_p['maxstep'], grid_size=grid_p['grid_size'], rad_energy_ig=rad_p['rad_energy_ig'], rad_rf=rad_p['rad_rf'], fb_wind_coef=fb_p['fb_wind_coef'], fb_wind_sd=fb_p['fb_wind_sd'], fb_wind_sd_transverse=fb_p['fb_wind_sd_transverse'], hardening_rad=hard_p['hardening_rad'], hardening_spo=hard_p['hardening_spo'], seed_hardening=hard_p['seed_hardening'], seed_spread=hard_p['seed_spread'], hardening_profile='matlab_inert' if scenario else 'matlab_active', rng_profile='seeded', output_dir=out_params['output_dir'], make_video=out_params['make_video'], dpi_hires=out_params['dpi_hires'], dump_interval=out_params['dump_interval'], dump_csv=out_params['dump_csv'], lazy_wind=out_params['lazy_wind'], dump_radiation_csv=out_params['dump_radiation_csv'], dump_spotting_csv=out_params['dump_spotting_csv'])
        self._queue_model.append_job(job)
        self.statusBar().showMessage(f'Job #{job.job_id} added to queue.')
        self._run_btn.setEnabled(True)

    def _run_all(self) -> None:
        pending = self._queue_model.pending_jobs()
        if not pending:
            QMessageBox.information(self, 'Nothing to Run', 'No pending jobs in the queue.')
            return
        self._add_btn.setEnabled(False)
        self._run_btn.setEnabled(False)
        self._cancel_btn.setEnabled(True)
        self._cancel_btn.setText('Cancel')
        self._progress.setValue(0)
        self._progress_label.setText('Running…')
        self._runner = JobRunner(pending, parent=self)
        self._runner.job_started.connect(self._on_job_started)
        self._runner.job_phase.connect(self._on_job_phase)
        self._runner.job_progress.connect(self._on_job_progress)
        self._runner.job_log.connect(self._on_job_log)
        self._runner.job_finished.connect(self._on_job_finished)
        self._runner.ask_continue.connect(self._on_ask_continue)
        self._runner.all_done.connect(self._on_all_done)
        self._runner.start()

    def _cancel_run(self) -> None:
        if not (self._runner and self._runner.isRunning()):
            return
        row = self._selected_queue_row()
        running_job_selected = False
        if row is not None:
            job = self._queue_model.job_at(row)
            if job is not None and job.status == 'Running':
                running_job_selected = True
        if running_job_selected:
            job = self._queue_model.job_at(row)
            ret = QMessageBox.question(self, 'Cancel Job', f'Cancel job #{job.job_id} and pause the queue?', QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if ret == QMessageBox.StandardButton.Yes:
                self._runner.cancel_current_job()
                self._cancel_btn.setEnabled(False)
                self.statusBar().showMessage(f'Cancelling job #{job.job_id}…')
        else:
            ret = QMessageBox.question(self, 'Cancel All Jobs', 'Stop the current simulation and cancel all remaining jobs?', QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if ret == QMessageBox.StandardButton.Yes:
                self._runner.requestInterruption()
                self._cancel_btn.setEnabled(False)
                self.statusBar().showMessage('Cancelling all jobs…')

    def _on_job_started(self, job_id: int) -> None:
        self._queue_model.update_status(job_id, STATUS_RUNNING)
        self._queue_model.update_start_time(job_id)
        self.statusBar().showMessage(f'Running job #{job_id}…')
        self._progress.setValue(0)
        self._progress_label.setText(f'Job #{job_id}')

    def _on_job_phase(self, job_id: int, phase: str) -> None:
        self._queue_model.update_phase(job_id, phase)
        self.statusBar().showMessage(f'Job #{job_id} — {phase}')

    def _on_job_progress(self, job_id: int, current: int, total: int) -> None:
        self._queue_model.update_progress(job_id, current, total)
        self._progress.setMaximum(total)
        self._progress.setValue(current)

    def _on_job_log(self, job_id: int, text: str) -> None:
        self._log.insertPlainText(text)
        scrollbar = self._log.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def _on_job_finished(self, job_id: int, success: bool, msg: str) -> None:
        self._queue_model.update_end_time(job_id)
        if success:
            self._queue_model.update_status(job_id, STATUS_DONE)
            self.statusBar().showMessage(f'Job #{job_id} completed successfully.')
        else:
            self._queue_model.update_status(job_id, STATUS_FAILED, msg)
            self._log.append(f'\n[Job #{job_id} FAILED]\n{msg}\n')
            self.statusBar().showMessage(f'Job #{job_id} failed.')

    def _on_ask_continue(self, cancelled_job_id: int) -> None:
        pending_count = len(self._queue_model.pending_jobs())
        ret = QMessageBox.question(self, 'Job Cancelled', f"Job #{cancelled_job_id} was cancelled.\n\nThere {('is' if pending_count == 1 else 'are')} {pending_count} remaining pending job{('s' if pending_count != 1 else '')}.\n\nContinue with the remaining jobs?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if ret == QMessageBox.StandardButton.Yes:
            self._runner.resume_queue()
            self._cancel_btn.setEnabled(True)
            self.statusBar().showMessage('Resuming queue…')
        else:
            self._runner.stop_queue()
            self.statusBar().showMessage('Queue stopped.')

    def _on_all_done(self) -> None:
        self._add_btn.setEnabled(True)
        self._run_btn.setEnabled(True)
        self._cancel_btn.setEnabled(False)
        self._progress_label.setText('Done')
        self._progress.setValue(self._progress.maximum())
        self._on_queue_selection_changed()
        QMessageBox.information(self, 'All Jobs Complete', 'All queued jobs have finished.')

    def _on_queue_selection_changed(self) -> None:
        row = self._selected_queue_row()
        has_selection = row is not None
        job = self._queue_model.job_at(row) if row is not None else None
        is_pending = job is not None and job.status == STATUS_PENDING
        not_running = self._runner is None or not self._runner.isRunning()
        self._remove_btn.setEnabled(has_selection and is_pending and not_running)
        self._dup_btn.setEnabled(has_selection)

    def _selected_queue_row(self) -> int | None:
        indexes = self._queue_view.selectionModel().selectedRows()
        if indexes:
            return indexes[0].row()
        return None

    def _remove_selected_job(self) -> None:
        row = self._selected_queue_row()
        if row is None:
            return
        job = self._queue_model.job_at(row)
        if job is None or job.status != STATUS_PENDING:
            QMessageBox.information(self, 'Cannot Remove', 'Only Pending jobs can be removed.\nRunning/Done/Failed jobs are kept for reference.')
            return
        self._queue_model.remove_job(row)
        self.statusBar().showMessage(f'Job #{job.job_id} removed from queue.')

    def _duplicate_selected_job(self) -> None:
        row = self._selected_queue_row()
        if row is None:
            return
        src = self._queue_model.job_at(row)
        if src is None:
            return
        self._queue_model.duplicate_job(row)
        self.statusBar().showMessage(f'Duplicated job #{src.job_id} → new Pending job added.')

    def _clear_queue(self) -> None:
        running = self._runner is not None and self._runner.isRunning()
        if running:
            QMessageBox.warning(self, 'Cannot Clear', 'A simulation is currently running. Cancel it before clearing the queue.')
            return
        if self._queue_model.rowCount() == 0:
            return
        ret = QMessageBox.question(self, 'Clear Queue', 'Remove all jobs from the queue?', QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if ret == QMessageBox.StandardButton.Yes:
            self._queue_model.clear_all()
            self._remove_btn.setEnabled(False)
            self._dup_btn.setEnabled(False)
            self.statusBar().showMessage('Queue cleared.')

    def _queue_context_menu(self, pos) -> None:
        index = self._queue_view.indexAt(pos)
        if not index.isValid():
            return
        row = index.row()
        job = self._queue_model.job_at(row)
        if job is None:
            return
        menu = QMenu(self)
        not_running = self._runner is None or not self._runner.isRunning()
        act_dup = menu.addAction('Duplicate Job')
        act_dup.triggered.connect(lambda: self._queue_model.duplicate_job(row))
        if job.status == STATUS_PENDING and not_running:
            menu.addSeparator()
            act_remove = menu.addAction('Remove Job')
            act_up = menu.addAction('Move Up')
            act_down = menu.addAction('Move Down')
            act_remove.triggered.connect(lambda: self._queue_model.remove_job(row))
            act_up.triggered.connect(lambda: self._queue_model.move_up(row))
            act_down.triggered.connect(lambda: self._queue_model.move_down(row))
        if job.status == STATUS_FAILED:
            menu.addSeparator()
            act_err = menu.addAction('Show Error…')
            act_err.triggered.connect(lambda: self._show_error(job))
        if job.status == STATUS_DONE:
            menu.addSeparator()
            act_open = menu.addAction('Open Output Folder')
            act_open.triggered.connect(lambda: self._open_job_output(job))
        menu.exec(self._queue_view.viewport().mapToGlobal(pos))

    def _show_job_detail(self, index) -> None:
        job = self._queue_model.job_at(index.row())
        if job and job.status == STATUS_FAILED and job.error_msg:
            self._show_error(job)
            return
        if job:
            from swuift.timezones import local_to_utc, utc_isoformat

            start_utc = utc_isoformat(local_to_utc(job.t_start, job.timezone))
            end_utc = utc_isoformat(local_to_utc(job.t_end, job.timezone))
            QMessageBox.information(
                self,
                f'Job #{job.job_id}',
                f'Status: {job.status}\n'
                f'Local time: {job.t_start.isoformat(sep=" ")} → '
                f'{job.t_end.isoformat(sep=" ")}\n'
                f'Timezone: {job.timezone}\n'
                f'UTC: {start_utc} → {end_utc}\n'
                f'Steps: {job.maxstep}',
            )

    def _show_error(self, job: JobConfig) -> None:
        dlg = QMessageBox(self)
        dlg.setWindowTitle(f'Error – Job #{job.job_id}')
        dlg.setDetailedText(job.error_msg)
        dlg.setText('The job failed with the following error:')
        dlg.exec()

    def _open_job_output(self, job: JobConfig) -> None:
        from PySide6.QtCore import QUrl
        from PySide6.QtGui import QDesktopServices

        QDesktopServices.openUrl(QUrl.fromLocalFile(job.output_dir))

    def _apply_marshall_defaults(self, config: dict) -> None:
        self._grid_tab.apply_scenario_config(config)
        self._rad_tab.load_settings({
            'rad_energy_ig': config['rad_ig_thresh'],
            'rad_rf': config['rad_decay'],
        })
        self._fb_tab.load_settings({
            'fb_wind_coef': config['brand_wind_coef'],
            'fb_wind_sd': config['brand_wind_sd'],
            'fb_wind_sd_transverse': config['brand_wind_sd_lat'],
        })
        self._hard_tab.load_settings({
            'hardening_rad': config['harden_rad'],
            'hardening_spo': config['harden_spo'],
            'seed_hardening': config['seed_harden'],
            'seed_spread': config['seed_spread'],
        })
        self._out_tab.set_marshall_defaults()
        self.statusBar().showMessage('Marshall defaults applied: 121 steps, 13.875 m grid, seeded profiles.')

    def _show_about(self) -> None:
        license_path = os.path.join(RESOURCE_DIR, 'LICENSE')
        license_name = 'SWUIFT Research and Academic Use License'
        if os.path.isfile(license_path):
            try:
                with open(license_path, encoding='utf-8') as handle:
                    first = next((line.strip() for line in handle if line.strip()), license_name)
                    license_name = first
            except OSError:
                pass
        QMessageBox.about(
            self,
            'About SWUIFT',
            f'<h3>SWUIFT {APP_VERSION}</h3>'
            '<p>Streamlined Wildland-Urban Interface Fire Tracing</p>'
            f'<p><b>Build:</b> {BUILD_ID}<br><b>License:</b> {license_name}</p>'
            '<p>License and third-party notices are included with this application.</p>',
        )

    def _collect_all_settings(self) -> dict:
        grid_p = self._grid_tab.get_params()
        return {'data': self._data_tab.get_data_params(), 'grid': {'t_start': grid_p['t_start'].isoformat() if grid_p['t_start'] else None, 't_end': grid_p['t_end'].isoformat() if grid_p['t_end'] else None, 'timezone': grid_p['timezone'], 'maxstep': grid_p['maxstep'], 'grid_size': grid_p['grid_size']}, 'radiation': self._rad_tab.get_params(), 'firebrands': self._fb_tab.get_params(), 'hardening': self._hard_tab.get_params(), 'output': self._out_tab.get_params()}

    def _apply_all_settings(self, d: dict) -> None:
        if 'data' in d:
            self._data_tab.load_settings(d['data'])
        if 'grid' in d:
            self._grid_tab.load_settings(d['grid'])
        if 'radiation' in d:
            self._rad_tab.load_settings(d['radiation'])
        if 'firebrands' in d:
            self._fb_tab.load_settings(d['firebrands'])
        if 'hardening' in d:
            self._hard_tab.load_settings(d['hardening'])
        if 'output' in d:
            self._out_tab.load_settings(d['output'])

    def _save_settings_json(self) -> None:
        path, _ = QFileDialog.getSaveFileName(self, 'Save Settings', APP_DIR, 'JSON files (*.json)')
        if not path:
            return
        try:
            data = self._collect_all_settings()
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, default=str)
            self.statusBar().showMessage(f'Settings saved to {path}')
        except Exception as exc:
            QMessageBox.critical(self, 'Save Failed', str(exc))

    def _load_settings_json(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, 'Load Settings', APP_DIR, 'JSON files (*.json)')
        if not path:
            return
        try:
            with open(path, encoding='utf-8') as f:
                data = json.load(f)
            self._apply_all_settings(data)
            self.statusBar().showMessage(f'Settings loaded from {path}')
        except Exception as exc:
            QMessageBox.critical(self, 'Load Failed', str(exc))

    def _restore_settings(self) -> None:
        qs = QSettings(_ORG, _APP)
        geom = qs.value('geometry')
        if geom:
            self.restoreGeometry(geom)
        state = qs.value('windowState')
        if state:
            self.restoreState(state)
        json_str = qs.value('lastSettings')
        if json_str:
            try:
                data = json.loads(json_str)
                self._apply_all_settings(data)
            except Exception:
                pass

    def _persist_settings(self) -> None:
        qs = QSettings(_ORG, _APP)
        qs.setValue('geometry', self.saveGeometry())
        qs.setValue('windowState', self.saveState())
        try:
            data = self._collect_all_settings()
            qs.setValue('lastSettings', json.dumps(data, default=str))
        except Exception:
            pass

    def closeEvent(self, event) -> None:
        if self._runner and self._runner.isRunning():
            ret = QMessageBox.question(self, 'Simulation Running', 'A simulation is currently running. Quit anyway?', QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if ret != QMessageBox.StandardButton.Yes:
                event.ignore()
                return
            self._runner.requestInterruption()
            self._runner.wait(3000)
        self._persist_settings()
        super().closeEvent(event)
