# Configuration file for the Sphinx documentation builder.
#
# This file only contains a selection of the most common options. For a full
# list see the documentation:
# http://www.sphinx-doc.org/en/master/config

# -- Path setup --------------------------------------------------------------

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.


import os
import sys


def remove_text_block(filepath, start_delimiter, end_delimiter):
    """ This function removes a delimited text block form the input file"""

    with open(filepath, "r+") as f:
        lines = f.readlines()
        f.seek(0)

        write = True
        for line in lines:
            if start_delimiter in line:
                write = False
                continue
            if end_delimiter in line:
                write = True
                continue
            if write:
                f.write(line)


_here = os.path.abspath(os.path.dirname(__file__))
_library_root = os.path.abspath(os.path.join(_here, "../.."))

remove_text_block(
    "{}/README.md".format(_here),
    "<!-- MarkdownTOC -->",
    "<!-- /MarkdownTOC -->",
)


sys.path.insert(0, _library_root)


about = {}
with open("{}/wirepas_backend_client/__about__.py".format(_library_root)) as f:
    exec(f.read(), about)

# -- Project information -----------------------------------------------------
_project = about["__title__"]
_copyright = "{},{}".format(about["__copyright__"], about["__license__"])
_release = about["__version__"]
_name = about["__pkg_name__"]
_version = about["__version__"]
_description = about["__description__"]
_author = about["__author__"]
_author_email = about["__author_email__"]
_url = about["__url__"]
_license = about["__license__"]
_classifiers = about["__classifiers__"]
_keywords = about["__keywords__"]


# -- General configuration ---------------------------------------------------
extensions = [
    "m2r",
    "sphinx.ext.napoleon",
    "sphinx.ext.todo",
    "sphinx.ext.coverage",
    "sphinx.ext.imgmath",
    "sphinx.ext.ifconfig",
    "sphinx.ext.viewcode",
    "sphinx.ext.githubpages",
    "sphinxcontrib.apidoc",
]

language = None
master_doc = "index"
source_suffix = [".rst", ".md"]

pygments_style = "sphinx"
templates_path = ["_templates"]

exclude_patterns = ["setup"]

# -- Options for apidoc output -------------------------------------------------
apidoc_module_dir = os.path.join(_library_root, "wirepas_backend_client")
apidoc_excluded_paths = ["tests", "setup"]
apidoc_separate_modules = False
apidoc_module_first = True

# -- Options for autodoc output -------------------------------------------------
autodoc_mock_imports = [
    "mysqlclient",
    "pandas",
    "yaml",
    "paho",
    "wirepas_messaging",
    "fluent",
]

# -- Options for HTML output -------------------------------------------------
html_theme = "alabaster"
html_theme_options = {
    "logo": "logo.png",
    "github_user": "wirepas",
    "github_repo": "backend-client",
    "travis_button": True,
    "page_width": "1024px",
    "description": _description,
}
html_static_path = ["_static"]
html_favicon = "_static/favicon.png"
html_sidebars = {
    "**": ["about.html", "navigation.html", "relations.html", "searchbox.html"]
}


# -- Options for HTMLHelp output ---------------------------------------------

# Output file base name for HTML help builder.
htmlhelp_basename = _name


# -- Options for LaTeX output ------------------------------------------------

latex_elements = {
    # The paper size ('letterpaper' or 'a4paper').
    #
    "papersize": "a4paper",
    # The font size ('10pt', '11pt' or '12pt').
    #
    "pointsize": "11pt",
    # Additional stuff for the LaTeX preamble.
    #
    # 'preamble': '',
    # Latex figure (float) alignment
    #
    # 'figure_align': 'htbp',
}

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title,
#  author, documentclass [howto, manual, or own class]).
latex_documents = [
    (
        master_doc,
        "wirepasbackendclient.tex",
        "Wirepas Backend Client Source Documentation",
        "Wirepas Ltd.",
        "manual",
    )
]
