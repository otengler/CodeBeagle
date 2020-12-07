#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""QDarkStyle is a dark stylesheet for Python and Qt applications."""

# pylint: disable=invalid-name

# Standard library imports
import logging
import os
import platform
import warnings

from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import QCoreApplication, QFile, QTextStream
from PyQt5.QtGui import QColor, QPalette

# Local imports
from qdarkstyle.palette import DarkPalette
from qdarkstyle.constants import PACKAGE_PATH, QSS_FILE

from qdarkstyle import style_rc

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
    package_dir = os.path.basename(PACKAGE_PATH)
    qss_rc_path = ":" + os.path.join(package_dir, QSS_FILE)

    _logger.debug("Reading QSS file in: %s", qss_rc_path)

    # It gets the qss file from compiled style_rc that was import
    # not from the file QSS as we are using resources
    qss_file = QFile(qss_rc_path)

    stylesheet = ""

    if qss_file.exists():
        qss_file.open(QFile.ReadOnly | QFile.Text)
        text_stream = QTextStream(qss_file)
        stylesheet = text_stream.readAll()
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

