from __future__ import annotations
from dataclasses import dataclass, field
import numpy as np
from .config import SWUIFTConfig
__all__ = ['HardeningResult', 'apply_hardening', 'apply_hardening_profile']

@dataclass
class HardeningResult:
    criteria_rad: np.ndarray = field(repr=False)
    criteria_spo: np.ndarray = field(repr=False)
    knownig_mat: np.ndarray = field(repr=False)

def apply_hardening(cfg: SWUIFTConfig, binary_cover: np.ndarray, homes_mat: np.ndarray, hardening_mat_rad: np.ndarray, hardening_mat_spo: np.ndarray, knownig_mat: np.ndarray, lati: np.ndarray, long: np.ndarray) -> HardeningResult:
    if cfg.seed_hardening is None:
        raise ValueError("Active hardening requires seed_hardening.")
    rng = np.random.RandomState(cfg.seed_hardening)
    rows = lati.shape[0]
    cols = long.shape[0]
    limrad = cfg.limrad
    limspo = cfg.limspo
    mask_rad = (binary_cover == 1) & (hardening_mat_rad != 1)
    mask_spo = (binary_cover == 1) & (hardening_mat_spo != 1)
    mat_1_rad = np.zeros((rows, cols))
    mat_1_spo = np.zeros((rows, cols))
    mat_1_rad[mask_rad] = homes_mat[mask_rad]
    mat_1_spo[mask_spo] = homes_mat[mask_spo]
    vector_1_rad = np.unique(mat_1_rad)
    vector_1_rad = vector_1_rad[vector_1_rad != 0]
    vector_1_spo = np.unique(mat_1_spo)
    vector_1_spo = vector_1_spo[vector_1_spo != 0]
    n_rad = len(vector_1_rad)
    n_spo = len(vector_1_spo)
    rand_vals_rad = rng.rand(n_rad) if n_rad > 0 else np.empty(0)
    rand_vals_spo = rng.rand(n_spo) if n_spo > 0 else np.empty(0)
    criteria_rad = np.zeros((rows, cols))
    for i in range(n_rad):
        hid = int(vector_1_rad[i])
        r = float(rand_vals_rad[i])
        criteria_rad[(homes_mat == hid) & (binary_cover == 1)] = r
    criteria_spo = np.zeros((rows, cols))
    for i in range(n_spo):
        hid = int(vector_1_spo[i])
        r = float(rand_vals_spo[i])
        criteria_spo[(homes_mat == hid) & (binary_cover == 1)] = r
    rad_hid_set = set((int(h) for h in vector_1_rad))
    spo_hid_set = set((int(h) for h in vector_1_spo))
    knownig_out = knownig_mat.copy()
    criteria_ave = (criteria_rad + criteria_spo) / 2.0
    limave = (limspo + limrad) / 2.0
    for i in range(rows):
        for j in range(cols):
            hid = int(homes_mat[i, j]) if homes_mat[i, j] > 0 else 0
            if hid == 0:
                continue
            if binary_cover[i, j] != 1:
                continue
            in_rad = hid in rad_hid_set
            in_spo = hid in spo_hid_set
            if (in_rad or in_spo) and criteria_ave[i, j] > limave:
                knownig_out[i, j] = 0
    return HardeningResult(criteria_rad=criteria_rad, criteria_spo=criteria_spo, knownig_mat=knownig_out)


def apply_hardening_profile(
    cfg: SWUIFTConfig,
    binary_cover: np.ndarray,
    homes_mat: np.ndarray,
    hardening_mat_rad: np.ndarray,
    hardening_mat_spo: np.ndarray,
    knownig_mat: np.ndarray,
    lati: np.ndarray,
    long: np.ndarray,
) -> HardeningResult:
    """Apply the scenario's MATLAB-compatible hardening behavior.

    Camp and Marshall have the negative-ID assignment loops commented in their
    legacy drivers. Their criteria arrays therefore remain zero and known
    ignitions are unchanged. ``matlab_inert`` reproduces that behavior without
    silently repairing the original MATLAB model.
    """
    if cfg.hardening_profile == "matlab_inert":
        shape = np.asarray(binary_cover).shape
        return HardeningResult(
            criteria_rad=np.zeros(shape, dtype=np.float64),
            criteria_spo=np.zeros(shape, dtype=np.float64),
            knownig_mat=np.asarray(knownig_mat, dtype=np.float64).copy(),
        )
    if cfg.hardening_profile != "matlab_active":
        raise ValueError(f"Unknown hardening profile: {cfg.hardening_profile!r}")
    return apply_hardening(
        cfg,
        binary_cover,
        homes_mat,
        hardening_mat_rad,
        hardening_mat_spo,
        knownig_mat,
        lati,
        long,
    )
