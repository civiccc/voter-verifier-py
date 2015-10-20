#!/usr/bin/env bash
set -exuo pipefail

total=230000000 # <- approximately correct value:
for FILE in $(env/bin/python list_files.py); do
  echo "Processing file $(basename $FILE)..." >&2
  wget \
    --timeout 900 \
    --output-document - \
    --quiet \
    $FILE \
    | gunzip
done | pv -l -s $total | env/bin/python index.py $total
