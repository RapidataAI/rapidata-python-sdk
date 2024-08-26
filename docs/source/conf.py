# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

import sys
from pathlib import Path
import toml

# Get the absolute path to the root of your project
project_root = Path(__file__).parents[2].resolve()

# Add the project root and the src directory to the Python path
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src"))

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

project = "Rapidata Python SDK"
copyright = "2024, Rapidata"
author = "Rapidata"

pyproject_toml_path = project_root / "pyproject.toml"
with open(pyproject_toml_path, "r") as f:
    pyproject_toml = toml.load(f)
    release = pyproject_toml["tool"]["poetry"]["version"]

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = ["autoapi.extension", "sphinx.ext.viewcode", "myst_parser"]

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


# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = "furo"
html_static_path = ["_static"]
