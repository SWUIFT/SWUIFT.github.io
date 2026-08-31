import sys
import os
from pathlib import Path
from PyInstaller.utils.hooks import collect_data_files, copy_metadata

block_cipher = None

_imageio_ffmpeg_binaries = collect_data_files(
    "imageio_ffmpeg", includes=["binaries/ffmpeg*"]
)
_swuift_datas = collect_data_files("swuift", includes=["resources/scenarios/*.json"])
_tzdata_datas = collect_data_files("tzdata")
_desktop = Path.cwd().resolve()
_root = _desktop.parent.parent
_legal_datas = [
    (str(_root / "LICENSE"), "."),
    (str(_root / "THIRD_PARTY_NOTICES.md"), "."),
]
_generated_datas = [
    (str(path), ".")
    for path in (
        _desktop / "SWUIFT.icns",
        _desktop / "SWUIFT.ico",
        _desktop / "SWUIFT.png",
        _desktop / "BUILD_INFO",
    )
    if path.is_file()
]

ICON_MACOS = "SWUIFT.icns"
ICON_WIN = "SWUIFT.ico"
ICON_LINUX = "SWUIFT.png"
ICON = ICON_MACOS if sys.platform == "darwin" else ICON_WIN if sys.platform == "win32" else ICON_LINUX

a = Analysis(
    ["swuift_app.py"],
    pathex=[".", "../../packages/cli", "../../packages/core/src"],
    binaries=_imageio_ffmpeg_binaries,
    datas=[
        ("gui", "gui"),
        *_swuift_datas,
        *_tzdata_datas,
        *copy_metadata("swuift"),
        *copy_metadata("imageio"),
        *copy_metadata("imageio-ffmpeg"),
        *copy_metadata("tzdata"),
        *_legal_datas,
        *_generated_datas,
    ],
    hiddenimports=[
        "numpy",
        "scipy",
        "scipy.io",
        "scipy.io.matlab",
        "h5py",
        "h5py._hl",
        "h5py._hl.files",
        "matplotlib",
        "matplotlib.backends.backend_agg",
        "imageio",
        "imageio_ffmpeg",
        "tqdm",
        "tqdm.auto",
        "av",
        "PySide6",
        "PySide6.QtCore",
        "PySide6.QtGui",
        "PySide6.QtWidgets",
        "PIL",
        "PIL.Image",
        "swuift",
        "swuift.config",
        "swuift.data_loader",
        "swuift.license",
        "swuift.plotting",
        "swuift.scenario",
        "swuift.simulation",
        "swuift.timezones",
        "tzdata",
        "swuift_core",
        "swuift_core.kernels",
        "swuift_core.spread",
        "swuift_core.hardening",
        "swuift_core.config",
        "numba",
        "numba.core",
        "numba.np",
        "llvmlite",
        "llvmlite.binding",
    ],
    excludes=[
        "tkinter",
        "PyQt5",
        "PyQt6",
    ],
    noarchive=False,
    cipher=block_cipher,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="SWUIFT",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    icon=ICON,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="SWUIFT",
)

if sys.platform == "darwin":
    app = BUNDLE(
        coll,
        name="SWUIFT.app",
        icon=ICON_MACOS,
        bundle_identifier="edu.buffalo.swuift",
        info_plist={
            "CFBundleName": "SWUIFT",
            "CFBundleDisplayName": "SWUIFT",
            "CFBundleVersion": "1.0.0",
            "CFBundleShortVersionString": "1.0.0",
            "NSHighResolutionCapable": True,
            "NSRequiresAquaSystemAppearance": False,
            "LSMinimumSystemVersion": "11.0",
        },
    )
