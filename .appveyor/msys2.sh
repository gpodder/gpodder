#!/bin/bash

set -e

cd tools/win_installer
# bash -xe to also see commands
bash -e ./build.sh "${APPVEYOR_REPO_COMMIT}"
