#!/bin/bash
#
# Generates the Sphinx documentation
#
# Copyright 2019 Wirepas Ltd

cd docs || exit 1
rm -rf wm-bcli || true
make html
mv -vT build/html/ wm-bcli/ || true
rm -rf build || true
