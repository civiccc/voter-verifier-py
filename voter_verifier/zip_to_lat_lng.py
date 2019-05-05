import csv

from collections import namedtuple

from voter_verifier.config import ZIP_TO_LAT_LNG_FILE_NAME

LatLng = namedtuple('LatLng', ['lat', 'lng'])

class ZipToLatLng:
  """ A class for serving a zip_code to lat/lng dictionary. Dict is loaded from
      CSV file.
  """
  def __init__(self):
    with open(ZIP_TO_LAT_LNG_FILE_NAME, 'rb') as csvfile:
      reader = csv.reader(csvfile, delimiter=',')
      self.zip_to_lat_lng_map = {row[0]: LatLng(row[5],row[6]) for row in reader}

  # Returns string representation that can be passed to ES as geo_point
  def get_lat_lng_str(self, zip_code):
    zip_lat_lng = self.zip_to_lat_lng_map.get(zip_code)
    return '%s, %s' % (zip_lat_lng.lat, zip_lat_lng.lng) if zip_lat_lng else None

  def get_lat(self, zip_code):
    zip_lat_lng = self.zip_to_lat_lng_map.get(zip_code)
    return zip_lat_lng.lat if zip_lat_lng else None

  def get_lng(self, zip_code):
    zip_lat_lng = self.zip_to_lat_lng_map.get(zip_code)
    return zip_lat_lng.lat if zip_lat_lng else None