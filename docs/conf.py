import os
import sys

sys.path.insert(0, os.path.abspath(".."))

project = "PimPam"
copyright = "PimPam Contributors"
author = "PimPam Contributors"
release = "0.1.0"

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.viewcode",
    "sphinx.ext.napoleon",
]

html_theme = "furo"
html_title = "PimPam API Docs"
html_theme_options = {
    "sidebar_hide_name": False,
}

exclude_patterns = ["_build"]
