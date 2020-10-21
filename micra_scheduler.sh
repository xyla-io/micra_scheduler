#!/bin/bash
source .venv/bin/activate
DEFAULT_CONFIG='development'
[[ -n $1 ]] && DEFAULT_CONFIG=$1
python run.py $@
