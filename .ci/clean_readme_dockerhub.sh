#!/usr/bin/env bash

cp README.rst README.hub
sed -i "/.. _image/d" README.hub
sed -i "/.. _/d" README.hub
sed -i "/::/d" README.hub
sed -i "/:target:/d" README.hub
