"""Canonical physics configuration for SWUIFT simulation."""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal, Optional

import numpy as np

GRID_SIZE: float = 10.0
T_STEP_MIN: float = 5.0
T_START_DEFAULT: datetime = datetime(2025, 1, 7, 18, 20, 0)
T_END_DEFAULT: datetime = datetime(2025, 1, 8, 14, 20, 0)
AES: float = 60.0
EE: float = 0.7
ER: float = 0.7
SCONST: float = 5.67e-08
RAD_ENERGY_IG_DEFAULT: float = 14000.0
RAD_RF_DEFAULT: float = 1.0
FB_MASS: float = 0.5
FB_DIST_MU: float = 0.01
FB_DIST_SD: float = 0.5
FB_WIND_COEF_DEFAULT: float = 30.0
FB_WIND_SD_DEFAULT: float = 0.3
FB_WIND_SD_TRANSVERSE_DEFAULT: float = 4.85
HARDENING_RAD_DEFAULT: float = 70.0
HARDENING_SPO_DEFAULT: float = 70.0
SEED_HARDENING_DEFAULT: int = 123456
SEED_SPREAD_DEFAULT: int = 10
HardeningProfile = Literal["matlab_active", "matlab_inert"]
RNGProfile = Literal["seeded", "matlab_unseeded"]
_TMPR_VALUES: tuple[float, ...] = (
    28.62, 178.171, 192.151, 306.514, 484.043, 677.377, 680.536, 682.559,
    684.021, 685.132, 686.011, 686.728, 687.327, 687.837, 688.278, 688.665,
    689.008, 689.314, 689.59, 689.84, 690.068, 690.278, 690.471, 690.649,
    690.815, 690.969, 691.113, 691.248, 691.374, 691.493, 691.604, 691.709,
    691.808, 691.902, 691.99, 692.074, 678.551,
)
TMPR_DEFAULT: np.ndarray = np.array(_TMPR_VALUES, dtype=np.float64)


@dataclass(frozen=True)
class SWUIFTConfig:
    grid_size: float = GRID_SIZE
    t_start: datetime = field(default_factory=lambda: T_START_DEFAULT)
    t_end: datetime = field(default_factory=lambda: T_END_DEFAULT)
    t_step_min: float = T_STEP_MIN
    maxstep: Optional[int] = None
    aes: float = AES
    ee: float = EE
    er: float = ER
    sconst: float = SCONST
    rad_energy_ig: float = RAD_ENERGY_IG_DEFAULT
    rad_rf: float = RAD_RF_DEFAULT
    fb_mass: float = FB_MASS
    fb_wind_coef: float = FB_WIND_COEF_DEFAULT
    fb_wind_sd: float = FB_WIND_SD_DEFAULT
    fb_wind_sd_transverse: float = FB_WIND_SD_TRANSVERSE_DEFAULT
    fb_dist_mu: float = FB_DIST_MU
    fb_dist_sd: float = FB_DIST_SD
    veg_included: bool = True
    tmpr: np.ndarray = field(default_factory=lambda: TMPR_DEFAULT.copy())
    hardening_level_rad: float = HARDENING_RAD_DEFAULT
    hardening_level_spo: float = HARDENING_SPO_DEFAULT
    seed_hardening: Optional[int] = SEED_HARDENING_DEFAULT
    seed_spread: Optional[int] = SEED_SPREAD_DEFAULT
    hardening_profile: HardeningProfile = "matlab_active"
    rng_profile: RNGProfile = "seeded"
    scenario_id: Optional[str] = None

    @property
    def fstep(self) -> int:
        return int(22 / self.t_step_min) + 1

    @property
    def lstep(self) -> int:
        return int(177 / self.t_step_min) + 1

    @property
    def fb_str_ig(self) -> int:
        return math.ceil(24 / self.fb_mass)

    @property
    def fb_veg_gen(self) -> int:
        return math.ceil(self.grid_size ** 2 / (2.25 * math.pi / 4) * (87 / self.fb_mass))

    @property
    def fb_veg_ig(self) -> int:
        return 64 * math.ceil(3.5 / self.fb_mass) + 1

    @property
    def limrad(self) -> float:
        return 1.0 - self.hardening_level_rad / 100.0

    @property
    def limspo(self) -> float:
        return 1.0 - self.hardening_level_spo / 100.0

    def __hash__(self):
        return id(self)

    def __eq__(self, other):
        return self is other
