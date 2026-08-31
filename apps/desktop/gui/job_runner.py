from __future__ import annotations

import io
import json
import os
import sys
import threading
import time
import traceback
from datetime import datetime

from PySide6.QtCore import QThread, Signal

from .job_queue import JobConfig


class _StreamRedirect(io.TextIOBase):
    def __init__(self, callback):
        super().__init__()
        self._cb = callback

    def write(self, s: str) -> int:
        if s:
            self._cb(s)
        return len(s)

    def flush(self):
        pass


class JobRunner(QThread):
    job_started = Signal(int)
    job_phase = Signal(int, str)
    job_progress = Signal(int, int, int)
    job_log = Signal(int, str)
    job_finished = Signal(int, bool, str)
    ask_continue = Signal(int)
    all_done = Signal()

    def __init__(self, jobs: list[JobConfig], parent=None) -> None:
        super().__init__(parent)
        self._jobs = jobs
        self._cancel_current: bool = False
        self._stop_after_current: bool = False
        self._continue_event = threading.Event()
        self._user_wants_continue: bool = False

    def cancel_current_job(self) -> None:
        self._cancel_current = True

    def resume_queue(self) -> None:
        self._user_wants_continue = True
        self._continue_event.set()

    def stop_queue(self) -> None:
        self._user_wants_continue = False
        self._continue_event.set()

    def run(self) -> None:
        for job in self._jobs:
            if self.isInterruptionRequested() or self._stop_after_current:
                break
            self._run_one(job)
        self.all_done.emit()

    def _run_one(self, job: JobConfig) -> None:
        self._cancel_current = False
        self.job_started.emit(job.job_id)
        try:
            from swuift.config import build_config
            from swuift.data_loader import load_all_extracted, load_scenario_data
            from swuift.license import load_license
            from swuift.scenario import load_scenario_manifest
            from swuift.simulation import SimulationCancelledError, run_simulation
            from swuift.timezones import local_to_utc, localized_timestamp, utc_isoformat
        except ImportError as exc:
            self.job_finished.emit(job.job_id, False, f"Import error: {exc}")
            return
        job_id = job.job_id

        def _progress(n: int, total: int):
            self.job_progress.emit(job_id, n, total)

        def _log_cb(text: str):
            self.job_log.emit(job_id, text)

        redir = _StreamRedirect(_log_cb)
        old_stdout = sys.stdout
        old_stderr = sys.stderr
        sys.stdout = redir
        sys.stderr = redir
        data = None
        try:
            license_info = load_license()
            self.job_phase.emit(job_id, "Loading data")
            if job.data_mode == "scenario":
                manifest = load_scenario_manifest(job.scenario_id)
                data = load_scenario_data(
                    manifest,
                    job.data_root,
                    preload_wind=not job.lazy_wind,
                )
            else:
                data = load_all_extracted(
                    wildland_fire_matrix_file=job.wildland_fire_matrix,
                    domain_matrix_file=job.domain_matrix,
                    binary_cover_file=job.binary_cover,
                    homes_matrix_file=job.homes_matrix,
                    latitude_file=job.latitude,
                    longitude_file=job.longitude,
                    radiation_matrix_file=job.radiation_matrix,
                    spotting_matrix_file=job.spotting_matrix,
                    water_matrix_file=job.water_matrix,
                    wind_file=job.wind_file,
                    preload_wind=not job.lazy_wind,
                )
            self.job_phase.emit(job_id, "Building config")
            t_start_utc = local_to_utc(job.t_start, job.timezone)
            t_end_utc = local_to_utc(job.t_end, job.timezone)
            cfg = build_config(
                grid_size=job.grid_size,
                t_start=t_start_utc,
                t_end=t_end_utc,
                max_steps=job.maxstep,
                harden_rad=job.hardening_rad,
                harden_spo=job.hardening_spo,
                rad_ig_thresh=job.rad_energy_ig,
                rad_decay=job.rad_rf,
                brand_wind_coef=job.fb_wind_coef,
                brand_wind_sd=job.fb_wind_sd,
                brand_wind_sd_lat=job.fb_wind_sd_transverse,
                seed_harden=job.seed_hardening,
                seed_spread=job.seed_spread,
                hardening_profile=job.hardening_profile,
                rng_profile=job.rng_profile,
                scenario_id=job.scenario_id or None,
            )
            stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            out_dir = os.path.join(job.output_dir, f"run_{stamp}")
            base = out_dir
            suffix = 2
            while os.path.exists(out_dir):
                out_dir = f"{base}-{suffix}"
                suffix += 1
            os.makedirs(out_dir, exist_ok=True)
            if self.isInterruptionRequested() or self._cancel_current:
                self.job_finished.emit(job_id, False, "Cancelled before simulation.")
                self._handle_post_cancel(job_id)
                return
            self.job_phase.emit(job_id, "Simulating")
            run_started = datetime.now().astimezone()
            run_clock = time.perf_counter()

            def _phase_cb(phase: str):
                self.job_phase.emit(job_id, phase)

            simulation_metadata = run_simulation(
                cfg,
                data,
                out_dir,
                frame_dpi=job.dpi_hires,
                dump_every=job.dump_interval,
                dump_csv=job.dump_csv,
                out_frames=True,
                out_video=job.make_video,
                out_gif=job.make_video,
                out_ig_plots=True,
                out_fire_csv=True,
                out_buildings_csv=True,
                out_rad_steps=job.dump_radiation_csv,
                out_spo_steps=job.dump_spotting_csv,
                emit_metrics=True,
                emit_frame_state=True,
                checkpoint_every=0,
                forensic_full=False,
                progress_callback=_progress,
                cancellation_callback=lambda: (
                    self._cancel_current or self.isInterruptionRequested()
                ),
                phase_callback=_phase_cb,
                display_timezone=job.timezone,
            )
            run_ended = datetime.now().astimezone()
            with open(os.path.join(out_dir, "run_params.json"), "w", encoding="utf-8") as handle:
                json.dump(
                    {
                        "schema_version": 1,
                        "source": "desktop",
                        "started_at": run_started.isoformat(),
                        "ended_at": run_ended.isoformat(),
                        "elapsed_seconds": time.perf_counter() - run_clock,
                        "license": {
                            "accepted": True,
                            "path": str(license_info.path),
                            "sha256": license_info.sha256,
                        },
                        "config": {
                            "timezone": job.timezone,
                            "t_start_entered": job.t_start.isoformat(sep=" "),
                            "t_end_entered": job.t_end.isoformat(sep=" "),
                            "t_start_utc": utc_isoformat(t_start_utc),
                            "t_end_utc": utc_isoformat(t_end_utc),
                            "t_start_local": localized_timestamp(t_start_utc, job.timezone)[
                                "local"
                            ],
                            "t_end_local": localized_timestamp(t_end_utc, job.timezone)["local"],
                            "grid_size": cfg.grid_size,
                            "max_steps": cfg.maxstep,
                        },
                        "simulation_metadata": simulation_metadata,
                    },
                    handle,
                    indent=2,
                )
            self.job_phase.emit(job_id, "Done")
            self.job_finished.emit(job_id, True, "")
        except SimulationCancelledError:
            self.job_finished.emit(job_id, False, "Cancelled by user.")
            self._handle_post_cancel(job_id)
        except Exception:
            tb = traceback.format_exc()
            self.job_finished.emit(job_id, False, tb)
        finally:
            if data is not None:
                data.close()
            sys.stdout = old_stdout
            sys.stderr = old_stderr

    def _handle_post_cancel(self, job_id: int) -> None:
        remaining = [j for j in self._jobs if j.status not in ("Done", "Failed", "Running")]
        if remaining and (not self.isInterruptionRequested()):
            self._continue_event.clear()
            self.ask_continue.emit(job_id)
            self._continue_event.wait()
            if not self._user_wants_continue:
                self._stop_after_current = True
        else:
            self._stop_after_current = True
