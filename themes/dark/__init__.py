#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""QDarkStyle is a dark stylesheet for Python and Qt applications."""

# pylint: disable=invalid-name

# Standard library imports
import logging
import os
import platform
import pathlib
from typing import cast

from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import QFile, QTextStream
from PyQt5.QtGui import QColor, QPalette

# Local imports
from .palette import DarkPalette
from .constants import PACKAGE_PATH, QSS_FILE

_logger = logging.getLogger(__name__)

def _apply_os_patches() -> str:
    """
    Apply OS-only specific stylesheet patches.

    Returns:
        str: stylesheet string (css).
    """
    os_fix = ""

    if platform.system().lower() == 'darwin':
        # See issue #12
        os_fix = '''
        QDockWidget::title
        {{
            background-color: {color};
            text-align: center;
            height: 12px;
        }}
        '''.format(color=DarkPalette.COLOR_BACKGROUND_NORMAL)

    # Only open the QSS file if any patch is needed
    if os_fix:
        _logger.info("Found OS patches to be applied.")

    return os_fix

def _apply_application_patches(app: QApplication) -> None:
    """
    Apply application level fixes on the QPalette.

    The import names args must be passed here because the import is done
    inside the load_stylesheet() function, as QtPy is only imported in
    that moment for setting reasons.
    """
    # See issue #139
    color = DarkPalette.COLOR_SELECTION_LIGHT
    qcolor = QColor(color)

    _logger.info("Found application patches to be applied.")

    if app:
        palette = app.palette()
        palette.setColor(QPalette.Normal, QPalette.Link, qcolor)
        app.setPalette(palette)
    else:
        _logger.warning("No QCoreApplication instance found. "
                        "Application patches not applied. "
                        "You have to call load_stylesheet function after "
                        "instantiation of QApplication to take effect. ")


def apply_stylesheet(app: QApplication, additionalStyles: str = "") -> None:
    """
    Load the stylesheet for use in a PyQt5 application.

    Returns:
        str: the stylesheet string.
    """

    # Thus, by importing the binary we can access the resources
    scriptDir = pathlib.Path(__file__).parent.resolve()
    qss_rc_path = os.path.join(scriptDir, QSS_FILE)

    _logger.debug("Reading QSS file in: %s", qss_rc_path)

    # It gets the qss file from compiled style_rc that was import
    # not from the file QSS as we are using resources
    qss_file = QFile(qss_rc_path)

    stylesheet = ""

    if qss_file.exists():
        qss_file.open(cast(QFile.OpenModeFlag, QFile.OpenModeFlag.ReadOnly | QFile.OpenModeFlag.Text))
        text_stream = QTextStream(qss_file)
        stylesheet = text_stream.readAll()

        # Replace the marker <RC_DIR> with the relative path to the 'rc' directory. This is needed because the path differs when
        # packaged with cx_freeze or run directly.
        scriptDirPath = pathlib.Path(scriptDir)
        scriptDirPathRelToCwd = str(scriptDirPath.relative_to(os.getcwd())).replace("\\", "/")
        stylesheet = stylesheet.replace("<RC_DIR>", scriptDirPathRelToCwd)

        _logger.info("QSS file sucessfuly loaded.")
    else:
        stylesheet = ""
        raise FileNotFoundError("Unable to find QSS file '{}' resources.".format(qss_rc_path))

    _logger.debug("Checking patches for being applied.")

    stylesheet += _apply_os_patches()
    if additionalStyles:
        stylesheet += additionalStyles

    _apply_application_patches(app)

    app.setStyleSheet(stylesheet)

