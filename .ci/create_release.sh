#!/usr/bin/env bash

set -e

GIT_TAG="${1}"
GIT_MESSAGE="${2:-"release ${GIT_TAG}"}"

echo "creating changelog..."
github_changelog_generator -t "${GH_TOKEN}" --no-unreleased

echo "creating ${GIT_TAG}: ${GIT_MESSAGE}"
git tag -m "${GIT_MESSAGE}" "${GIT_TAG}"

echo "done"
