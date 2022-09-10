#!/usr/bin/with-contenv bashio
set -e

echo "Hello BMS Pace"

# cd "${0%/*}"
cd /workdir
python3 -u ./bms.py #"$@"