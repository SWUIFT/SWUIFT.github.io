from __future__ import annotations

import os
import sys
from importlib.metadata import PackageNotFoundError, version

from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QDialogButtonBox,
    QLabel,
    QMessageBox,
    QPlainTextEdit,
    QVBoxLayout,
)
from swuift.license import LicenseInfo, load_license

APP_DIR: str = os.path.dirname(os.path.abspath(sys.argv[0]))
RESOURCE_DIR: str = getattr(sys, "_MEIPASS", os.path.dirname(os.path.dirname(__file__)))


def _asset_path(name: str) -> str:
    return os.path.join(RESOURCE_DIR, name)


def platform_icon_path() -> str:
    names = (
        ("SWUIFT.icns", "SWUIFT.png", "SWUIFT.ico")
        if sys.platform == "darwin"
        else ("SWUIFT.ico", "SWUIFT.png", "SWUIFT.icns")
        if sys.platform == "win32"
        else ("SWUIFT.png", "SWUIFT.ico", "SWUIFT.icns")
    )
    return next((_asset_path(name) for name in names if os.path.isfile(_asset_path(name))), "")


try:
    APP_VERSION = version("swuift")
except PackageNotFoundError:
    APP_VERSION = "1.0.0"
try:
    with open(_asset_path("BUILD_INFO"), encoding="utf-8") as handle:
        BUILD_ID = handle.read().strip() or "development"
except OSError:
    BUILD_ID = os.environ.get("SWUIFT_BUILD_ID", "development")
_ICON_PATH: str = platform_icon_path()


def _license_dialog(license_info: LicenseInfo) -> QDialog:
    dialog = QDialog()
    dialog.setWindowTitle("SWUIFT License Agreement")
    dialog.setModal(True)
    dialog.resize(820, 680)
    layout = QVBoxLayout(dialog)

    heading = QLabel(
        "You must read and accept the complete SWUIFT license each time the application starts."
    )
    heading.setWordWrap(True)
    layout.addWidget(heading)

    path_label = QLabel(f"Local license file: {license_info.path}")
    path_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
    path_label.setWordWrap(True)
    layout.addWidget(path_label)

    license_text = QPlainTextEdit()
    license_text.setPlainText(license_info.text)
    license_text.setReadOnly(True)
    license_text.setLineWrapMode(QPlainTextEdit.LineWrapMode.WidgetWidth)
    layout.addWidget(license_text, 1)

    buttons = QDialogButtonBox()
    agree = buttons.addButton("I Agree", QDialogButtonBox.ButtonRole.AcceptRole)
    decline = buttons.addButton(
        "Decline and Exit",
        QDialogButtonBox.ButtonRole.RejectRole,
    )
    agree.clicked.connect(dialog.accept)
    decline.clicked.connect(dialog.reject)
    layout.addWidget(buttons)
    return dialog


def run() -> None:
    from .main_window import MainWindow

    app = QApplication(sys.argv)
    app.setApplicationName("SWUIFT")
    app.setOrganizationName("SWUIFT")
    app.setOrganizationDomain("buffalo.edu")
    if os.path.isfile(_ICON_PATH):
        app.setWindowIcon(QIcon(_ICON_PATH))
    try:
        license_info = load_license()
    except (FileNotFoundError, RuntimeError) as exc:
        QMessageBox.critical(None, "SWUIFT License Missing", str(exc))
        return
    if _license_dialog(license_info).exec() != QDialog.DialogCode.Accepted:
        return
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
