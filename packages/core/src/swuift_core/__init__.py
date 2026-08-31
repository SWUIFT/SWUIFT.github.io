"""Shared SWUIFT physics core."""

from swuift_core.config import SWUIFTConfig
from swuift_core.hardening import HardeningResult, apply_hardening, apply_hardening_profile
from swuift_core.kernels import (
    brand_transport_kernel,
    kernel_backend,
    max_brands_in_circle,
    radiation_kernel,
)
from swuift_core.spread import brand_gen, brand_ig, radiation_gen, radiation_ig

__all__ = [
    "SWUIFTConfig",
    "HardeningResult",
    "apply_hardening",
    "apply_hardening_profile",
    "brand_gen",
    "brand_ig",
    "brand_transport_kernel",
    "kernel_backend",
    "max_brands_in_circle",
    "radiation_gen",
    "radiation_ig",
    "radiation_kernel",
]
