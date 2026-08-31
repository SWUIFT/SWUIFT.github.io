"""Load SWUIFT input data from .mat and .csv files.

Small files (v5) are read with ``scipy.io.loadmat``.
The ~7 GB wind file (v7.3 / HDF5) is read with ``h5py``.

Wind is auto-preloaded into RAM by default for fast per-step access.
Use lazy_wind=True to fall back to per-step HDF5 reads (slow but low RAM).
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Tuple

import h5py
import numpy as np
import scipy.io as sio


# ---------------------------------------------------------------------------
# Small MAT-file helpers
# ---------------------------------------------------------------------------

def _load_v5(path: str, squeeze: bool = True) -> dict:
    return sio.loadmat(path, squeeze_me=squeeze)


def _load_single_v5(path: str, var_name: str) -> np.ndarray:
    """Load a single variable from a MATLAB v5 file as float64."""
    d = _load_v5(path, squeeze=True)
    if var_name not in d:
        raise KeyError(f"Variable {var_name!r} not found in {path!r}")
    arr = np.asarray(d[var_name], dtype=np.float64)
    # Ravel 1-column matrices for vectors (common for lati/long).
    if arr.ndim == 2 and arr.shape[1] == 1:
        arr = arr.ravel()
    return arr


def _load_csv(path: str) -> np.ndarray:
    arr = np.loadtxt(path, delimiter=",", dtype=np.float64)
    return np.asarray(arr, dtype=np.float64)


def _load_array(path: str, mat_var_name: str) -> np.ndarray:
    ext = Path(path).suffix.lower()
    if ext == ".mat":
        return _load_single_v5(path, mat_var_name)
    if ext == ".csv":
        return _load_csv(path)
    raise ValueError(f"Unsupported input format for {path!r}: expected .mat or .csv")


def load_default_values(data_dir: str) -> dict:
    path = os.path.join(data_dir, "default_values.mat")
    return _load_v5(path)


def load_domains(data_dir: str) -> np.ndarray:
    path = os.path.join(data_dir, "domains_mat.mat")
    d = _load_v5(path)
    return np.asarray(d["domains_mat"], dtype=np.float64)


def load_eaton_inputs(data_dir: str) -> dict:
    path = os.path.join(data_dir, "eaton_inputs_all.mat")
    d = _load_v5(path)
    out = {}
    for key in ("binary_cover", "hardening_mat_rad", "hardening_mat_spo",
                "homes_mat", "water"):
        out[key] = np.asarray(d[key], dtype=np.float64)
    out["lati"] = np.asarray(d["lati"], dtype=np.float64).ravel()
    out["long"] = np.asarray(d["long"], dtype=np.float64).ravel()
    return out


def load_fire_prog(data_dir: str) -> np.ndarray:
    path = os.path.join(data_dir, "fire_prog.mat")
    d = _load_v5(path)
    return np.asarray(d["fire_prog"], dtype=np.float64)


# ---------------------------------------------------------------------------
# Wind data (HDF5 / v7.3)
# ---------------------------------------------------------------------------

class WindData:
    """Accessor for the wind arrays with preload (default) or lazy mode.

    On-disk HDF5 shape (MATLAB column-major saved to HDF5):
        wind_s, wind_d : (T, cols, rows) = (247, 1792, 1148)

    We expose ``get_slice(tstep)`` returning ``(rows, cols)`` 2-D arrays.
    """

    def __init__(
        self,
        path: str,
        preload: bool = True,
        expected_shape: tuple[int, int] | None = None,
    ):
        # Accept either a directory containing ``wind_eaton.mat`` (legacy mode)
        # or a direct path to a wind .mat file (e.g. extracted ``wind.mat``).
        self._h5: h5py.File | None = None
        self._ws = None
        self._wd = None

        self._preloaded = False
        self.wind_s_all: np.ndarray | None = None
        self.wind_d_all: np.ndarray | None = None

        self._cache: dict[int, Tuple[np.ndarray, np.ndarray]] = {}

        if os.path.isdir(path):
            path = os.path.join(path, "wind_eaton.mat")

        ext = Path(path).suffix.lower()
        if ext == ".mat":
            self._h5 = h5py.File(path, "r")
            self._ws = self._h5["wind_s"]
            self._wd = self._h5["wind_d"]
            self.n_timesteps = self._ws.shape[0]
            if preload:
                self._preload()
        elif ext == ".csv":
            if expected_shape is None:
                raise ValueError(
                    "expected_shape is required when loading wind from CSV."
                )
            self._load_csv_pair(path, expected_shape)
        else:
            raise ValueError(
                f"Unsupported wind format for {path!r}: expected .mat or .csv"
            )

    def _load_csv_pair(self, csv_marker_path: str, expected_shape: tuple[int, int]) -> None:
        marker = Path(csv_marker_path)
        rows, cols = expected_shape
        candidate_speed = [marker.with_name(f"{marker.stem}_s.csv"), marker.with_name("wind_s.csv")]
        candidate_dir = [marker.with_name(f"{marker.stem}_d.csv"), marker.with_name("wind_d.csv")]
        speed_path = next((p for p in candidate_speed if p.exists()), None)
        dir_path = next((p for p in candidate_dir if p.exists()), None)
        if speed_path is None or dir_path is None:
            raise ValueError(
                "Wind CSV inputs require companion files in the same directory: "
                "'wind_s.csv' and 'wind_d.csv' (or '<wind_stem>_s.csv' and "
                "'<wind_stem>_d.csv')."
            )

        ws2d = _load_csv(str(speed_path))
        wd2d = _load_csv(str(dir_path))
        if ws2d.shape != (rows, cols) or wd2d.shape != (rows, cols):
            raise ValueError(
                "Wind CSV dimensions are incompatible: "
                f"expected {(rows, cols)}, got speed={ws2d.shape}, direction={wd2d.shape}"
            )

        self.wind_s_all = np.ascontiguousarray(ws2d[:, :, np.newaxis])
        self.wind_d_all = np.ascontiguousarray(wd2d[:, :, np.newaxis])
        self.n_timesteps = 1
        self._preloaded = True

    def _preload(self):
        if self._ws is None or self._wd is None:
            return
        raw_s = self._ws[()]
        raw_d = self._wd[()]
        self.wind_s_all = np.ascontiguousarray(np.transpose(raw_s, (2, 1, 0)))
        self.wind_d_all = np.ascontiguousarray(np.transpose(raw_d, (2, 1, 0)))
        self._preloaded = True

    def get_slice(self, tstep_0based: int) -> Tuple[np.ndarray, np.ndarray]:
        if self._preloaded:
            return (
                self.wind_s_all[:, :, tstep_0based],
                self.wind_d_all[:, :, tstep_0based],
            )
        if tstep_0based in self._cache:
            return self._cache[tstep_0based]
        if self._ws is None or self._wd is None:
            raise RuntimeError("Wind datasets are unavailable for lazy loading.")
        ws = np.ascontiguousarray(self._ws[tstep_0based, :, :].T)
        wd = np.ascontiguousarray(self._wd[tstep_0based, :, :].T)
        self._cache[tstep_0based] = (ws, wd)
        return ws, wd

    def close(self):
        if self._h5 is not None:
            self._h5.close()

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()


class ArrayWindData:
    """In-memory wind accessor for MATLAB v5 scenario bundles."""

    def __init__(self, wind_s: np.ndarray, wind_d: np.ndarray):
        speed = np.asarray(wind_s, dtype=np.float64)
        direction = np.asarray(wind_d, dtype=np.float64)
        if speed.ndim == 2:
            speed = speed[:, :, np.newaxis]
        if direction.ndim == 2:
            direction = direction[:, :, np.newaxis]
        if speed.ndim != 3 or direction.ndim != 3 or speed.shape != direction.shape:
            raise ValueError(
                "Wind arrays must have matching rows x cols x time shapes; "
                f"got speed={speed.shape}, direction={direction.shape}"
            )
        self.wind_s_all = np.ascontiguousarray(speed)
        self.wind_d_all = np.ascontiguousarray(direction)
        self.n_timesteps = int(speed.shape[2])

    def get_slice(self, tstep_0based: int) -> Tuple[np.ndarray, np.ndarray]:
        if tstep_0based < 0 or tstep_0based >= self.n_timesteps:
            raise IndexError(f"Wind timestep {tstep_0based} is out of range.")
        return self.wind_s_all[:, :, tstep_0based], self.wind_d_all[:, :, tstep_0based]

    def close(self) -> None:
        return None


# ---------------------------------------------------------------------------
# All-in-one loader
# ---------------------------------------------------------------------------

@dataclass
class SWUIFTData:
    """Container for every array the simulation needs."""
    binary_cover: np.ndarray = field(repr=False)
    hardening_mat_rad: np.ndarray = field(repr=False)
    hardening_mat_spo: np.ndarray = field(repr=False)
    homes_mat: np.ndarray = field(repr=False)
    water: np.ndarray = field(repr=False)
    lati: np.ndarray = field(repr=False)
    long: np.ndarray = field(repr=False)
    domains_mat: np.ndarray = field(repr=False)
    knownig_mat: np.ndarray = field(repr=False)
    wind: WindData | ArrayWindData = field(repr=False)
    rows: int = 0
    cols: int = 0

    def close(self):
        self.wind.close()


def load_all(data_dir: str, preload_wind: bool = True) -> Tuple[dict, SWUIFTData]:
    """Load everything.  Returns (defaults_dict, SWUIFTData).

    Wind is preloaded by default.  Pass ``preload_wind=False`` for lazy HDF5
    mode (low RAM, but ~29 s per step due to HDF5 transpose).
    """
    defaults = load_default_values(data_dir)
    domains = load_domains(data_dir)
    eaton = load_eaton_inputs(data_dir)
    fire_prog = load_fire_prog(data_dir)
    wind = WindData(data_dir, preload=preload_wind)

    rows, cols = eaton["binary_cover"].shape

    data = SWUIFTData(
        binary_cover=eaton["binary_cover"],
        hardening_mat_rad=eaton["hardening_mat_rad"],
        hardening_mat_spo=eaton["hardening_mat_spo"],
        homes_mat=eaton["homes_mat"],
        water=eaton["water"],
        lati=eaton["lati"],
        long=eaton["long"],
        domains_mat=domains,
        knownig_mat=fire_prog.copy(),
        wind=wind,
        rows=rows,
        cols=cols,
    )

    _validate_raster_shapes(data)
    return defaults, data


def _validate_raster_shapes(data: SWUIFTData) -> None:
    """Ensure all rasters share a consistent (rows, cols) grid and vectors match."""
    rows, cols = data.rows, data.cols
    expected = (rows, cols)

    grids = {
        "binary_cover": data.binary_cover,
        "hardening_mat_rad": data.hardening_mat_rad,
        "hardening_mat_spo": data.hardening_mat_spo,
        "homes_mat": data.homes_mat,
        "water": data.water,
        "domains_mat": data.domains_mat,
        "knownig_mat": data.knownig_mat,
    }

    for name, arr in grids.items():
        if arr.shape != expected:
            raise ValueError(
                f"Incompatible shape for {name}: expected {expected}, got {arr.shape}"
            )

    lati = np.asarray(data.lati).ravel()
    long = np.asarray(data.long).ravel()
    if lati.size != rows:
        raise ValueError(
            f"Incompatible latitude length: expected {rows}, got {lati.size}"
        )
    if long.size != cols:
        raise ValueError(
            f"Incompatible longitude length: expected {cols}, got {long.size}"
        )


def load_all_extracted(
    *,
    wildland_fire_matrix_file: str,
    domain_matrix_file: str,
    binary_cover_file: str,
    homes_matrix_file: str,
    latitude_file: str,
    longitude_file: str,
    radiation_matrix_file: str,
    spotting_matrix_file: str,
    water_matrix_file: str | None = None,
    wind_file: str,
    preload_wind: bool = True,
) -> SWUIFTData:
    """Load data in the extracted-per-variable format into a SWUIFTData.

    This matches the streamlined "extracted" mode described in
    EG_FAST_DATA_CONSUMPTION.md and performs strict dimension compatibility
    checks on all rasters and coordinate vectors.
    """
    knownig_mat = _load_array(wildland_fire_matrix_file, "wildland_fire_matrix")
    domains_mat = _load_array(domain_matrix_file, "domains_mat")
    binary_cover = _load_array(binary_cover_file, "binary_cover")
    homes_mat = _load_array(homes_matrix_file, "homes_mat")
    lati = _load_array(latitude_file, "lati").ravel()
    long = _load_array(longitude_file, "long").ravel()
    hardening_mat_rad = _load_array(radiation_matrix_file, "hardening_mat_rad")
    hardening_mat_spo = _load_array(spotting_matrix_file, "hardening_mat_spo")

    rows, cols = binary_cover.shape
    water = (
        _load_array(water_matrix_file, "water")
        if water_matrix_file and str(water_matrix_file).strip()
        else np.zeros((rows, cols), dtype=np.float64)
    )
    wind = WindData(wind_file, preload=preload_wind, expected_shape=(rows, cols))

    data = SWUIFTData(
        binary_cover=binary_cover,
        hardening_mat_rad=hardening_mat_rad,
        hardening_mat_spo=hardening_mat_spo,
        homes_mat=homes_mat,
        water=water,
        lati=lati,
        long=long,
        domains_mat=domains_mat,
        knownig_mat=knownig_mat,
        wind=wind,
        rows=rows,
        cols=cols,
    )

    _validate_raster_shapes(data)
    ws0, wd0 = data.wind.get_slice(0)
    if ws0.shape != (rows, cols) or wd0.shape != (rows, cols):
        raise ValueError(
            "Wind dimensions are incompatible with raster grid: "
            f"expected {(rows, cols)}, got speed={ws0.shape}, direction={wd0.shape}"
        )
    return data


def _load_mat_variable_any(path: Path, variable: str) -> np.ndarray:
    """Read one numeric variable from MATLAB v5 or v7.3/HDF5 files."""
    try:
        return np.asarray(_load_v5(str(path), squeeze=True)[variable], dtype=np.float64)
    except (NotImplementedError, ValueError, OSError):
        with h5py.File(path, "r") as handle:
            if variable not in handle:
                raise KeyError(f"Variable {variable!r} not found in {path}")
            raw = np.asarray(handle[variable][()], dtype=np.float64)
        # MATLAB v7.3 numeric arrays are exposed in reversed dimension order.
        if raw.ndim > 1:
            raw = np.transpose(raw, tuple(reversed(range(raw.ndim))))
        return raw
    except KeyError:
        raise


def _load_bundle_variables(path: Path, mapping: dict[str, str | None]) -> dict[str, np.ndarray]:
    result: dict[str, np.ndarray] = {}
    for target, source in mapping.items():
        if source is None:
            continue
        value = _load_mat_variable_any(path, source)
        result[target] = value.ravel() if target in {"lati", "long"} else value
    return result


def load_scenario_data(
    manifest: Any,
    data_root: str | Path,
    *,
    preload_wind: bool = True,
) -> SWUIFTData:
    """Load a manifest-described MATLAB scenario into the shared Python model."""
    root = manifest.validate_data_files(data_root)
    inputs = manifest.inputs
    bundle_path = root / inputs["bundle"]["file"]
    arrays = _load_bundle_variables(bundle_path, inputs["variables"])

    binary_cover = arrays["binary_cover"]
    homes_mat = arrays["homes_mat"]
    lati = arrays["lati"].ravel()
    long = arrays["long"].ravel()
    rows, cols = binary_cover.shape
    water = arrays.get("water", np.zeros((rows, cols), dtype=np.float64))

    domains = _load_mat_variable_any(
        root / inputs["domains"]["file"], inputs["domains"]["variable"]
    )
    known = _load_mat_variable_any(
        root / inputs["known_ignition"]["file"], inputs["known_ignition"]["variable"]
    )

    hardening = inputs["hardening"]
    if hardening["mode"] == "bundle_separate":
        hard_rad = _load_mat_variable_any(bundle_path, hardening["radiation_variable"])
        hard_spo = _load_mat_variable_any(bundle_path, hardening["spotting_variable"])
    elif hardening["mode"] == "single_map":
        standard = _load_mat_variable_any(root / hardening["file"], hardening["variable"])
        hard_rad = standard.copy()
        hard_spo = standard.copy()
    else:
        raise ValueError(f"Unsupported hardening input mode: {hardening['mode']!r}")

    wind_spec = inputs["wind"]
    speed_path = root / wind_spec["speed_file"]
    direction_path = root / wind_spec["direction_file"]
    combined_path = (
        root / wind_spec["combined_file"]
        if wind_spec.get("combined_file")
        else None
    )
    # MATLAB v7.3 reverses dimensions in HDF5, so a logical
    # rows-by-columns-by-time array is stored as time-by-columns-by-rows. Use
    # WindData for any combined HDF5 wind bundle to preserve lazy per-step
    # access (critical for Camp's multi-gigabyte expanded arrays).
    wind: WindData | ArrayWindData
    if combined_path is not None and h5py.is_hdf5(combined_path):
        wind = WindData(
            str(combined_path), preload=preload_wind, expected_shape=(rows, cols)
        )
    elif speed_path == direction_path and h5py.is_hdf5(speed_path):
        wind = WindData(
            str(speed_path), preload=preload_wind, expected_shape=(rows, cols)
        )
    else:
        speed = _load_mat_variable_any(speed_path, wind_spec["speed_variable"])
        direction = _load_mat_variable_any(direction_path, wind_spec["direction_variable"])
        wind = ArrayWindData(speed, direction)

    data = SWUIFTData(
        binary_cover=np.asarray(binary_cover, dtype=np.float64),
        hardening_mat_rad=np.asarray(hard_rad, dtype=np.float64),
        hardening_mat_spo=np.asarray(hard_spo, dtype=np.float64),
        homes_mat=np.asarray(homes_mat, dtype=np.float64),
        water=np.asarray(water, dtype=np.float64),
        lati=np.asarray(lati, dtype=np.float64),
        long=np.asarray(long, dtype=np.float64),
        domains_mat=np.asarray(domains, dtype=np.float64),
        knownig_mat=np.asarray(known, dtype=np.float64),
        wind=wind,
        rows=rows,
        cols=cols,
    )
    _validate_raster_shapes(data)
    ws0, wd0 = data.wind.get_slice(0)
    if ws0.shape != (rows, cols) or wd0.shape != (rows, cols):
        data.close()
        raise ValueError(
            "Wind dimensions are incompatible with raster grid: "
            f"expected {(rows, cols)}, got speed={ws0.shape}, direction={wd0.shape}"
        )
    expected_steps = int(manifest.config["expected_steps"])
    if data.wind.n_timesteps < expected_steps:
        data.close()
        raise ValueError(
            f"Wind contains {data.wind.n_timesteps} steps; {expected_steps} are required."
        )
    for name, value in {
        "binary_cover": data.binary_cover,
        "homes_mat": data.homes_mat,
        "domains_mat": data.domains_mat,
        "knownig_mat": data.knownig_mat,
    }.items():
        if not np.all(np.isfinite(value)):
            data.close()
            raise ValueError(f"{name} contains NaN or infinite values.")
    # MATLAB permits prescribed ignitions beyond the selected simulation
    # window; those cells are simply never selected by ``knownig_mat == tstep``.
    # Reject negative values, but preserve future scenario timesteps so Python
    # matches the untouched driver when a run uses only part of the input.
    if np.any(data.knownig_mat < 0):
        data.close()
        raise ValueError(
            "knownig_mat values must be non-negative one-based timesteps "
            "(with 0 meaning no prescribed ignition)."
        )
    return data
