#!/usr/bin/env bash
set -eux

SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )

rm -rf "${SCRIPT_DIR}/.tests"
mkdir -p "${SCRIPT_DIR}/.tests"
ln -s "${SCRIPT_DIR}/src/pattern_service" "${SCRIPT_DIR}/.tests/pattern_service"
cd "${SCRIPT_DIR}/.tests"
export PYTHONPATH="${SCRIPT_DIR}/.tests"
python pattern_service/manage.py makemigrations --merge --no-input
python pattern_service/manage.py migrate --no-input
python pattern_service/manage.py test core --verbosity=2
rm -rf "${SCRIPT_DIR}/.tests"