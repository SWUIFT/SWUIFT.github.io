from __future__ import annotations

import copy
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import List, Optional

from PySide6.QtCore import QAbstractTableModel, QModelIndex, Qt
from PySide6.QtGui import QBrush, QColor

STATUS_PENDING = 'Pending'
STATUS_RUNNING = 'Running'
STATUS_DONE = 'Done'
STATUS_FAILED = 'Failed'
_COLUMNS = ['#', 'Status', 'Phase', 'Elapsed / ETA', 'Output Dir']
_COL_ID = 0
_COL_STATUS = 1
_COL_PHASE = 2
_COL_TIME = 3
_COL_OUTDIR = 4
_STATUS_BG = {STATUS_PENDING: None, STATUS_RUNNING: QColor(255, 220, 80), STATUS_DONE: QColor(120, 210, 120), STATUS_FAILED: QColor(230, 90, 90)}
_FG_BLACK = QBrush(Qt.GlobalColor.black)
_id_counter = 0

def _next_id() -> int:
    global _id_counter
    _id_counter += 1
    return _id_counter

def _fmt_td(td: timedelta) -> str:
    total = int(td.total_seconds())
    if total < 0:
        return '—'
    h, rem = divmod(total, 3600)
    m, s = divmod(rem, 60)
    if h:
        return f'{h}h {m}m {s}s'
    if m:
        return f'{m}m {s}s'
    return f'{s}s'

@dataclass
class JobConfig:
    job_id: int = field(default_factory=_next_id)
    status: str = STATUS_PENDING
    error_msg: str = ''
    phase: str = ''
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    step_current: int = 0
    step_total: int = 0
    data_mode: str = 'extracted'
    scenario_id: str = ''
    data_root: str = ''
    wildland_fire_matrix: str = ''
    domain_matrix: str = ''
    binary_cover: str = ''
    homes_matrix: str = ''
    latitude: str = ''
    longitude: str = ''
    radiation_matrix: str = ''
    spotting_matrix: str = ''
    water_matrix: str = ''
    wind_file: str = ''
    t_start: datetime = field(default_factory=lambda: datetime(2025, 1, 7, 18, 20))
    t_end: datetime = field(default_factory=lambda: datetime(2025, 1, 8, 14, 20))
    timezone: str = 'UTC'
    maxstep: Optional[int] = None
    grid_size: float = 10.0
    hardening_profile: str = 'matlab_active'
    rng_profile: str = 'seeded'
    rad_energy_ig: float = 14000.0
    rad_rf: float = 1.0
    fb_wind_coef: float = 30.0
    fb_wind_sd: float = 0.3
    fb_wind_sd_transverse: float = 4.85
    hardening_rad: float = 70.0
    hardening_spo: float = 70.0
    seed_hardening: int = 123456
    seed_spread: int = 10
    output_dir: str = 'outputs'
    make_video: bool = True
    dpi_hires: int = 600
    dump_interval: int = 0
    dump_csv: bool = False
    lazy_wind: bool = False
    dump_radiation_csv: bool = False
    dump_spotting_csv: bool = False

class JobQueueModel(QAbstractTableModel):

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._jobs: List[JobConfig] = []

    def rowCount(self, parent: QModelIndex=QModelIndex()) -> int:
        return len(self._jobs)

    def columnCount(self, parent: QModelIndex=QModelIndex()) -> int:
        return len(_COLUMNS)

    def headerData(self, section: int, orientation: Qt.Orientation, role: int=Qt.ItemDataRole.DisplayRole):
        if role == Qt.ItemDataRole.DisplayRole and orientation == Qt.Orientation.Horizontal:
            return _COLUMNS[section]
        return None

    def data(self, index: QModelIndex, role: int=Qt.ItemDataRole.DisplayRole):
        if not index.isValid() or index.row() >= len(self._jobs):
            return None
        job = self._jobs[index.row()]
        col = index.column()
        if role == Qt.ItemDataRole.DisplayRole:
            if col == _COL_ID:
                return str(job.job_id)
            if col == _COL_STATUS:
                return job.status
            if col == _COL_PHASE:
                return job.phase
            if col == _COL_TIME:
                return self._format_time_cell(job)
            if col == _COL_OUTDIR:
                return job.output_dir
        if role == Qt.ItemDataRole.BackgroundRole:
            bg = _STATUS_BG.get(job.status)
            if bg is not None:
                return QBrush(bg)
        if role == Qt.ItemDataRole.ForegroundRole:
            if _STATUS_BG.get(job.status) is not None:
                return _FG_BLACK
        if role == Qt.ItemDataRole.ToolTipRole:
            if col == _COL_STATUS and job.error_msg:
                return job.error_msg
            if col == _COL_OUTDIR:
                return job.output_dir
        return None

    @staticmethod
    def _format_time_cell(job: JobConfig) -> str:
        if job.status == STATUS_PENDING:
            return ''
        now = datetime.now()
        if job.status == STATUS_RUNNING and job.start_time:
            elapsed = now - job.start_time
            elapsed_str = _fmt_td(elapsed)
            if job.step_total > 0 and job.step_current > 0:
                elapsed_secs = elapsed.total_seconds()
                rate = elapsed_secs / job.step_current
                remaining = rate * (job.step_total - job.step_current)
                eta_str = _fmt_td(timedelta(seconds=remaining))
                return f'{elapsed_str}  /  ETA {eta_str}'
            return elapsed_str
        if job.status in (STATUS_DONE, STATUS_FAILED):
            if job.start_time and job.end_time:
                total = job.end_time - job.start_time
                label = 'total' if job.status == STATUS_DONE else 'before fail'
                return f'{_fmt_td(total)} ({label})'
            return ''
        return ''

    def tick(self) -> None:
        for i, job in enumerate(self._jobs):
            if job.status == STATUS_RUNNING:
                idx = self.index(i, _COL_TIME)
                self.dataChanged.emit(idx, idx)

    def append_job(self, job: JobConfig) -> None:
        row = len(self._jobs)
        self.beginInsertRows(QModelIndex(), row, row)
        self._jobs.append(job)
        self.endInsertRows()

    def update_status(self, job_id: int, status: str, error_msg: str='') -> None:
        for i, job in enumerate(self._jobs):
            if job.job_id == job_id:
                job.status = status
                job.error_msg = error_msg
                idx_s = self.index(i, 0)
                idx_e = self.index(i, len(_COLUMNS) - 1)
                self.dataChanged.emit(idx_s, idx_e)
                return

    def update_phase(self, job_id: int, phase: str) -> None:
        for i, job in enumerate(self._jobs):
            if job.job_id == job_id:
                job.phase = phase
                idx = self.index(i, _COL_PHASE)
                self.dataChanged.emit(idx, idx)
                return

    def update_start_time(self, job_id: int) -> None:
        for i, job in enumerate(self._jobs):
            if job.job_id == job_id:
                job.start_time = datetime.now()
                idx = self.index(i, _COL_TIME)
                self.dataChanged.emit(idx, idx)
                return

    def update_end_time(self, job_id: int) -> None:
        for i, job in enumerate(self._jobs):
            if job.job_id == job_id:
                job.end_time = datetime.now()
                idx = self.index(i, _COL_TIME)
                self.dataChanged.emit(idx, idx)
                return

    def update_progress(self, job_id: int, current: int, total: int) -> None:
        for i, job in enumerate(self._jobs):
            if job.job_id == job_id:
                job.step_current = current
                job.step_total = total
                return

    def remove_job(self, row: int) -> None:
        if 0 <= row < len(self._jobs):
            self.beginRemoveRows(QModelIndex(), row, row)
            self._jobs.pop(row)
            self.endRemoveRows()

    def move_up(self, row: int) -> None:
        if row > 0:
            self._jobs[row], self._jobs[row - 1] = (self._jobs[row - 1], self._jobs[row])
            self.dataChanged.emit(self.index(row - 1, 0), self.index(row, len(_COLUMNS) - 1))

    def move_down(self, row: int) -> None:
        if row < len(self._jobs) - 1:
            self._jobs[row], self._jobs[row + 1] = (self._jobs[row + 1], self._jobs[row])
            self.dataChanged.emit(self.index(row, 0), self.index(row + 1, len(_COLUMNS) - 1))

    def duplicate_job(self, row: int) -> None:
        if 0 <= row < len(self._jobs):
            src = self._jobs[row]
            clone = copy.copy(src)
            clone.job_id = _next_id()
            clone.status = STATUS_PENDING
            clone.error_msg = ''
            clone.phase = ''
            clone.start_time = None
            clone.end_time = None
            clone.step_current = 0
            clone.step_total = 0
            self.append_job(clone)

    def clear_pending(self) -> None:
        pending_rows = [i for i, j in enumerate(self._jobs) if j.status == STATUS_PENDING]
        for row in reversed(pending_rows):
            self.beginRemoveRows(QModelIndex(), row, row)
            self._jobs.pop(row)
            self.endRemoveRows()

    def clear_all(self) -> None:
        self.beginResetModel()
        self._jobs.clear()
        self.endResetModel()

    def pending_jobs(self) -> List[JobConfig]:
        return [j for j in self._jobs if j.status == STATUS_PENDING]

    def job_at(self, row: int) -> Optional[JobConfig]:
        if 0 <= row < len(self._jobs):
            return self._jobs[row]
        return None
