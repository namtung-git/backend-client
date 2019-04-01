#!/usr/bin/env bash

set -e
set -x

black --check wirepas_backend_client/

#flake8
