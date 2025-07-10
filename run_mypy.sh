#!/usr/bin/env bash
set -eux

SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )

rm -rf "${SCRIPT_DIR}/.install"
mkdir -p "${SCRIPT_DIR}/.install"
ln -s "${SCRIPT_DIR}/src/pattern_service" "${SCRIPT_DIR}/.install/pattern_service"
cd "${SCRIPT_DIR}/.install"
export MYPYPATH="${SCRIPT_DIR}/.install"
mypy -p pattern_service
rm -rf "${SCRIPT_DIR}/.install"