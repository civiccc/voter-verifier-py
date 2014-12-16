import os
from ftplib import FTP_TLS


if __name__ == '__main__':
    username = 'brigade_media'
    password = os.environ['TARGETSMART_PASSWORD']
***REMOVED***

    ftp = FTP_TLS(hostname, username, password)
    base = '/outgoing/analysis20141211/brigade_media_analytic/'
    ftp.cwd(base)

    for f in ftp.nlst():
        print("ftp://" + hostname + base + f)
