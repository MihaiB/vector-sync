#! /usr/bin/env bash

set -ue -o pipefail
trap "echo >&2 script '${BASH_SOURCE[0]}' failed" ERR

SCRIPT=`readlink -e "${BASH_SOURCE[0]}"`
SCRIPT_DIR=`dirname "$SCRIPT"`
cd "$SCRIPT_DIR"/../..
unset SCRIPT SCRIPT_DIR

find -name '*.py' -exec python3 -m doctest '{}' +
python3 -m unittest
