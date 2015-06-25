# Make sure you have aws env variables (AWS_ACCESS_KEY_ID and
# AWS_SECRET_ACCESS_KEY)
import boto

FOLDER_NAME = '20150608analysis/'
# How long the download link is valid for before it expires
URL_VALID_TIME = 43200 # 12 hours

if __name__ == '__main__':
    conn = boto.connect_s3()

***REMOVED***
        # Print all files except for the folder itself
        if key.name == FOLDER_NAME: continue

        print key.generate_url(URL_VALID_TIME, query_auth=True)
