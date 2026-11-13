# -*- coding: utf-8 -*-
import os
from ..qss_generator import generate as generate_qss
from .palette import LightPalette


def generate() -> None:
    generate_qss(os.path.dirname(os.path.abspath(__file__)), LightPalette)
