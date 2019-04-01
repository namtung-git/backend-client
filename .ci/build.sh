#!/usr/bin/env bash

set -e
set -x

./utils/generate_wheel.sh
./utils/generate_sphinx_docs.sh || true

