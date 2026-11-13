# -*- coding: utf-8 -*-
"""Light theme palette.

The colors are used both to generate the light stylesheet (via
``generate_qss.py``) and to configure widgets that paint themselves, such as
``PathVisualizerDelegate``.
"""

from collections import OrderedDict
from typing import Any


class LightPalette:
    """Light theme variables."""

    # Selection
    COLOR_SELECTION_BACKGROUND = '#cde8ff'
    COLOR_SELECTION_FOREGROUND = '#1a1a1a'

    # Background gradient used by dialogs with shadeBackground=true
    COLOR_BACKGROUND_GRADIENT_START = 'rgb(220,235,255)'
    COLOR_BACKGROUND_GRADIENT_END = 'rgb(167,173,193)'

    # Flat button hover border
    COLOR_BUTTON_BORDER = '#8f8f91'

    # Path visualizer
    COLOR_PATH_NEW = '#323232'
    COLOR_PATH_SAME = '#969696'
    COLOR_PATH_FILE = '#000032'
    COLOR_PATH_SELECTED = '#323232'
    COLOR_PATH_SELECTED_FILE = '#000032'

    @classmethod
    def to_dict(cls) -> OrderedDict[str, Any]:
        """Convert variables to a dictionary used for SCSS generation."""
        order = [
            'COLOR_SELECTION_BACKGROUND',
            'COLOR_SELECTION_FOREGROUND',
            'COLOR_BACKGROUND_GRADIENT_START',
            'COLOR_BACKGROUND_GRADIENT_END',
            'COLOR_BUTTON_BORDER',
            'COLOR_PATH_NEW',
            'COLOR_PATH_SAME',
            'COLOR_PATH_FILE',
            'COLOR_PATH_SELECTED',
            'COLOR_PATH_SELECTED_FILE',
        ]
        dic: OrderedDict[str, Any] = OrderedDict()
        for var in order:
            dic[var] = getattr(cls, var)
        return dic
