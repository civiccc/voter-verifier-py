#!/usr/bin/env bash
set -e

echo "Finding total number of records..." >&2
# Cached value from running the below command:
total=228459351
***REMOVED***
# --user=brigade_media --password=$TARGETSMART_PASSWORD -O - | awk '{ sum+=$1} END {print sum}')
echo "... ${total} records" >&2

for FILE in $(python list_files.py); do
  echo "Processing file $(basename $FILE)..." >&2
  wget \
    --timeout 900 \
    --output-document - \
    --quiet \
    $FILE \
    | gunzip
done | pv -l -s $total | python index.py $total
