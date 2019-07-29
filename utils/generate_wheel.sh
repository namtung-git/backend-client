#!/usr/bin/env bash
# Copyright 2019 Wirepas Ltd
rm -f -r dist/
rm -f -r build/
py3clean .
python3 setup.py clean --all
python3 setup.py sdist bdist_wheel
