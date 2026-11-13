# -*- coding: utf-8 -*-
"""Shared generator for theme stylesheets.

A theme package provides a ``palette.py`` with a palette class exposing
``to_dict()`` and a ``qss`` directory containing ``main.scss`` and
``styles.scss``. The palette is written to ``_variables.scss`` and the
SCSS sources are compiled to ``style.qss``.
"""

from typing import Any
import os, subprocess


def sassExecutable() -> str:
    return os.environ["SASS"]


def generate(packagePath: str, palette: Any) -> None:
    qssPath = os.path.join(packagePath, "qss")
    mainScssFilepath = os.path.join(qssPath, "main.scss")
    stylesScssFilepath = os.path.join(qssPath, "styles.scss")
    # Generated intermediate file: prefix with '_' like other generated files
    stylesScssFilepathProcessed = os.path.join(qssPath, "_styles.scss.processed")
    variablesScssFilepath = os.path.join(qssPath, "_variables.scss")
    qssFilepath = os.path.join(packagePath, "style.qss")

    _create_scss_variables(variablesScssFilepath, palette)
    subprocess.run([sassExecutable(), "--no-source-map", mainScssFilepath, stylesScssFilepathProcessed], check=True, shell=False)
    _replaceInFile(stylesScssFilepathProcessed, qssFilepath, "_qnot_", "!")


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
