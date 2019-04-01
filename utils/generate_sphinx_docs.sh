#!/bin/bash
#
# Generates the Sphinx documentation
#
# Wirepas Oy


sphinx-apidoc -f -o docs/source wirepas_backend_client
cd docs;
rm -rf wm-bcli || true
make html
mv -vT build/html/ wm-bcli/ || true
rm -rf build || true

