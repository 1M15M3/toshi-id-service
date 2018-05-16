#!/bin/bash
set -euo pipefail
IFS=$'\n\t'
if [ ! -d 'env' ]; then
    echo "setting up virtualenv"
    virtualenv -p python3 env
fi
if [ -e requirements-base.txt ]; then
    env/bin/pip -q install -r requirements-base.txt
fi
if [ -e requirements-development.txt ]; then
    env/bin/pip -q install -r requirements-development.txt
fi
if [ -e requirements-testing.txt ]; then
    env/bin/pip -q install -r requirements-testing.txt
fi

export DATABASE_URL=postgresql://sunjinlee:@localhost:5432/toshiid_dev
export REDIS_URL=redis://127.0.0.1:6379
export PGSQL_SSL_DISABLED=1

env/bin/python -m toshiid --port=8080
