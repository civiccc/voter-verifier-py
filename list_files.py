# This gets file URLs from HDFS
import requests
import os
import sys

***REMOVED***
# Since we have security turned off on webhdfs, we just need some value here.
# It can be anything, but not "verifier" since that user has write permissions
# and we don't want to accidentally delete files later.
USER='verifier_download'

def get_filenames():
***REMOVED***

    if resp.status_code != 200:
        os.stderr.write("Error fetching list of files from HDFS gateway!")
        os.stderr.write("This probably means we have enabled authentication on HDFS via HTTP")
        os.stderr.write("(TODO: Rewrite this script to support that)")
        os.stderr.write(resp.text)
        sys.exit(1)

    for f in resp.json()['FileStatuses']['FileStatus']:
        if f['type'] != 'FILE':
            continue

        name = f['pathSuffix']

***REMOVED***
        yield url

if __name__ == '__main__':
    for filename in get_filenames():
        print filename
