# -*- coding: utf-8 -*-
from typing import Any
import os, subprocess
from .constants import MAIN_SCSS_FILEPATH, STYLES_SCSS_FILEPATH_PROCESSED, QSS_FILEPATH, VARIABLES_SCSS_FILEPATH
from .palette import DarkPalette

def sassExecutable() -> str:
    return os.environ["SASS"]

def generate() -> None:
    _create_scss_variables(VARIABLES_SCSS_FILEPATH, DarkPalette)
    subprocess.run([sassExecutable(), "--no-source-map", MAIN_SCSS_FILEPATH, STYLES_SCSS_FILEPATH_PROCESSED], check=True, shell=False)
    _replaceInFile(STYLES_SCSS_FILEPATH_PROCESSED, QSS_FILEPATH, "_qnot_", "!")

def _dict_to_scss(data: dict[str, Any]) -> str:
    """Create a scss variables string from a dict."""
    lines = []
    template = "${}: {};"
    for key, value in data.items():
        line = template.format(key, value)
        lines.append(line)

    return '\n'.join(lines)

def _create_scss_variables(variables_scss_filepath: str, palette: Any) -> None:
    """Create a scss variables file."""
    paletteData = palette.to_dict()
    data = _dict_to_scss(paletteData) + '\n'

    with open(variables_scss_filepath, 'w') as f:
        f.write(data)

def _replaceInFile(inputFile: str, outputFile: str, replaceSource: str, replaceWith: str) -> None:
    with open(inputFile, 'r') as f:
        lines = f.readlines()
    result = []
    for line in lines:
        line = line.replace(replaceSource, replaceWith)
        result.append(line)
    with open(outputFile, 'w') as f:
        f.writelines(result)

