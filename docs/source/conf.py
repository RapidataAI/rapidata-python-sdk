# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

import sys
from pathlib import Path

# Get the absolute path to the root of your project
project_root = Path(__file__).parents[2].resolve()

# Add the project root and the src directory to the Python path
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src"))

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

project = "Rapidata Python"
copyright = "2024, Rapidata"
author = "Rapidata"
release = "0.1.0"

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = ["autoapi.extension", "sphinx.ext.viewcode", "myst_parser", "sphinx_gallery.gen_gallery"]

templates_path = ["_templates"]
exclude_patterns = []

nitpicky = True

# -- MyST Parser configuration -----------------------------------------------
# https://myst-parser.readthedocs.io/en/latest/configuration.html

# Indicate that both .md and .rst files should be treated as sources
source_suffix = {
    '.rst': 'restructuredtext',
    '.md': 'markdown',
}

# Set heading anchor depth (1-6)
myst_heading_anchors = 3

# Enables auto-generated header anchors
myst_anchor_sections = True

# Enables URL link resolution
myst_url_schemes = ["http", "https", "mailto"]


# -- AutoAPI configuration ---------------------------------------------------

autoapi_dirs = ['../../rapidata']
autoapi_type = "python"
# autoapi_keep_files = True

# -- Options for Sphinx Gallery ----------------------------------------------

sphinx_gallery_conf = {
    "examples_dirs": "../../examples",  # path to your example scripts
    "gallery_dirs": "gallery_auto_examples",  # path to where to save gallery generated output
}


# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = "furo"
html_static_path = ["_static"]
