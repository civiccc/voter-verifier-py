from datetime import date
from logging import INFO
from os import path
from pprint import pformat
from time import time
from unittest import TestCase

from dateutil.parser import parse
from mock import patch
from more_itertools import consume
from nose.tools import eq_
from pyelasticsearch import ElasticSearch
from verifier_date_utils import years_ago, NullableDate, day_of_year
***REMOVED***
    TIMEOUT, RETRIES, INDEX, SEARCH_TYPE_DISCOVER, SEARCH_TYPE_TOP,
    SEARCH_TYPE_AUTO_VERIFY)
***REMOVED***
***REMOVED***
    match_many, match_one)
***REMOVED***


ROOT_DIR = path.abspath(path.dirname(__file__))

# Set this to true to use a real local ES index for the tests instead of
# setting up a very small one. Most people won't have 45GB of index lying
# around, though, so we usually test against a smaller corpus we pull out of a
# JSON file and index at test time.
USE_REAL_ES_INDEX = False
es_client = ElasticSearch(ES_HOSTS, TIMEOUT, RETRIES)
es_client.logger.setLevel(INFO)
zip_to_lat_lng = ZipToLatLng()

class FixturelessVerifierTests(TestCase):
  """
  Verifier tests that don't use a big, tightly coupled ball of test data
  """
  index_name = 'test_' + INDEX

  def test_multi_part_last_name_search(self):
    match = fake_voter(first_name='Francisco',
                       last_name='Lopez',
                       st='CA',
                       dob=date(1980, 1, 1))

    index_fake_voters([match], self.index_name)
    voter = match_one(
        search_type=SEARCH_TYPE_DISCOVER,
        first_name='Francisco',
        last_name='Lopez Clark',
        dob=date(1980, 1, 1),
        state='CA',
        index=self.index_name)
    eq_(voter['id'], match['id'])

    voter = match_one(
        search_type=SEARCH_TYPE_DISCOVER,
        first_name='Francisco',
        last_name='J. Lopez',
        dob=date(1980, 1, 1),
        state='CA',
        index=self.index_name)
    eq_(voter['id'], match['id'])

  def test_compacted_last_name_search(self):
    match = fake_voter(first_name='Hugh',
                       last_name='McKee',
                       st='CA',
                       dob=date(1980, 1, 1))
    index_fake_voters([match], self.index_name)

    voter = match_one(
        search_type=SEARCH_TYPE_DISCOVER,
        first_name='Hugh',
        last_name='Mc Kee',
        dob=date(1980, 1, 1),
        state='CA',
        index=self.index_name)

    eq_(voter['id'], match['id'])

  def test_compacted_first_name_search(self):
    match = fake_voter(first_name='Anna Belle',
                       last_name='Smith',
                       st='CA',
                       dob=date(1980, 1, 1))
    index_fake_voters([match], self.index_name)

    voter = match_one(
        search_type=SEARCH_TYPE_DISCOVER,
        first_name='Annabelle',
        last_name='Smith',
        dob=date(1980, 1, 1),
        state='CA',
        index=self.index_name)

    eq_(voter['id'], match['id'])

  def test_compacted_middle_name_search(self):
    match = fake_voter(first_name='Anna',
                       middle_name='Mc Cormick',
                       last_name='Smyth',
                       st='CA',
                       dob=date(1980, 1, 1))
    index_fake_voters([match], self.index_name)
    voter = match_one(
        search_type=SEARCH_TYPE_DISCOVER,
        first_name='Anna',
        middle_name='McCormick',
        last_name='Smyth',
        dob=date(1980, 1, 1),
        state='CA',
        index=self.index_name)
    eq_(voter['id'], match['id'])


  def test_multi_part_indexed_last_name(self):
    match = fake_voter(first_name='Franky',
                       last_name='Zoomer Loopimer',
                       st='CA',
                       dob=date(1980, 1, 1))

    index_fake_voters([match], self.index_name)
    voter = match_one(
        search_type=SEARCH_TYPE_DISCOVER,
        first_name='Franky',
        last_name='Zoomer',
        dob=date(1980, 1, 1),
        state='CA',
        index=self.index_name)
    eq_(voter['id'], match['id'])

    voter = match_one(
        search_type=SEARCH_TYPE_DISCOVER,
        first_name='Franky',
        last_name='Loopimer',
        dob=date(1980, 1, 1),
        state='CA',
        index=self.index_name)
    eq_(voter['id'], match['id'])

    voter = match_one(
        search_type=SEARCH_TYPE_DISCOVER,
        first_name='Franky',
        last_name='Zoomer Loopimer',
        dob=date(1980, 1, 1),
        state='CA',
        index=self.index_name)
    eq_(voter['id'], match['id'])

  def test_name_city_state_score_boost(self):
    best_match = fake_voter(first_name='Markus',
                       last_name='Cooperus',
                       st='CA',
                       city='San Francisco')

    match2 = fake_voter(first_name='Markus',
                       last_name='Cooperus',
                       st='CA',
                       city='Berkeley')

    match3 = fake_voter(first_name='Markus',
                       last_name='Cooperus',
                       st='TX',
                       city='Dallas')

    index_fake_voters([best_match, match2, match2], self.index_name)
    voter = match_many(
        search_type=SEARCH_TYPE_DISCOVER,
        first_name='Markus',
        last_name='Cooperus',
        state='CA',
        city='San Francisco',
        index=self.index_name)

    eq_(voter[0]['_debug_score'], 10)
    eq_(voter[0]['id'], best_match['id'])

  def test_returns_voting_history(self):
    index_fake_voters([fake_voter(
               first_name='Lewis',
               last_name='Clark',
               st='CA',
               dob=date(1980, 1, 1))],
               self.index_name)

    voter = match_one(
        search_type=SEARCH_TYPE_DISCOVER,
        first_name='Lewis',
        last_name='Clark',
        dob=date(1980, 1, 1),
        state='CA',
        index=self.index_name)
    eq_(voter['general_2014'], False)
    eq_(voter['general_2012'], False)
    eq_(voter['general_2000'], False)
    eq_(voter['general_2008'], False)
    eq_(voter['general_2006'], False)
    eq_(voter['general_2004'], False)
    eq_(voter['general_2002'], False)
    eq_(voter['general_2000'], False)

  def test_registration_date(self):
    index_fake_voters([fake_voter(first_name='Lewis',
                                  last_name='Clark',
                                  st='NV',
                                  dob=date(1980, 1, 1),
                                  registration_date='2016-02-08')],
                                      self.index_name)
    voter = match_one(
        search_type=SEARCH_TYPE_DISCOVER,
        first_name='Lewis',
        last_name='Clark',
        dob=date(1980, 1, 1),
        state='NV',
        index=self.index_name)
    eq_(voter['registration_date'], '2016-02-08')

***REMOVED***
    best_match = fake_voter(first_name='Lewis',
                            last_name='Clark',
                            st='CA',
                            ts_st='FL',
                            dob=date(1980, 1, 1))

    index_fake_voters([
        fake_voter(first_name='Lewis',
                   last_name='Clark',
                   st='NV',
                   ts_st='ND',
                   dob=date(1980, 1, 1)),
        best_match],
        self.index_name)

    # Record with middle name wins
    voter = match_one(
        search_type=SEARCH_TYPE_DISCOVER,
        first_name='Lewis',
        last_name='Clark',
        dob=date(1980, 1, 1),
        state='FL',
        index=self.index_name)
    eq_(voter['id'], best_match['id'])

***REMOVED***
    best_match = fake_voter(first_name='Gary',
                            last_name='Kramer',
                            st='CA',
                            ts_st='FL',
                            dob=date(1980, 1, 1))

    index_fake_voters([
        fake_voter(first_name='Gary',
                   last_name='Kramer',
                   st='NV',
                   ts_st='ND',
                   dob=date(1980, 1, 1)),
        best_match],
        self.index_name)

    # Record with middle name wins
    voter = match_many(
        search_type=SEARCH_TYPE_DISCOVER,
        first_name='Gary',
        last_name='Kramer',
        dob=date(1980, 1, 1),
        state='FL',
        index=self.index_name)[0]
    eq_(voter['id'], best_match['id'])

  def test_middle_name_match_one(self):
    best_match = fake_voter(first_name='John',
                            last_name='Smith',
                            middle_name='Martin',
                            dob=date(1980, 1, 1))

    index_fake_voters([
        fake_voter(first_name='John',
                   last_name='Smith',
                   middle_name='Wilson',
                   dob=date(1980, 1, 1)),
        best_match],
        self.index_name)

    # Record with middle name wins
    voters = match_many(
        search_type=SEARCH_TYPE_DISCOVER,
        first_name='John',
        middle_name='Martin',
        last_name='Smith',
        dob=date(1980, 1, 1),
        index=self.index_name)
    eq_(voters[0]['id'], best_match['id'])

  def test_middle_name_match_many(self):
    best_match = fake_voter(first_name='Matthew',
                            last_name='Miller',
                            middle_name='Martin',
                            dob=date(1980, 1, 1))

    index_fake_voters([
        fake_voter(first_name='Matthew',
                   last_name='Miller',
                   middle_name='Wilson',
                   dob=date(1980, 1, 1)),
        best_match],
        self.index_name)

    # Record with middle name should be first
    voter = match_many(
        first_name='Matthew',
        middle_name='Martin',
        last_name='Miller',
        dob=date(1980, 1, 1),
        index=self.index_name,
        max_matches=3)[0]
    eq_(voter['id'], best_match['id'])

  def test_blank_middle_name(self):
    best_match = fake_voter(first_name='Gerry',
                            middle_name='',
                            last_name='Potter',
                            dob=date(1980, 1, 1))

    index_fake_voters([
        fake_voter(first_name='Gerry',
                   middle_name='Miller',
                   last_name='Potter',
                   dob=date(1980, 1, 1)),
        best_match],
        self.index_name)

    # Record with blank name should be first
    voter = match_many(
        search_type=SEARCH_TYPE_DISCOVER,
        first_name='Gerry',
        middle_name='',
        last_name='Potter',
        index=self.index_name,
        max_matches=3)[0]
    eq_(voter['id'], best_match['id'])

  def test_middle_initial_query_score(self):
    match = fake_voter(first_name='Sappirole',
                       last_name='Fragmenter',
                       middle_name='Driver',
                       dob=date(1980, 1, 1))

    index_fake_voters([match], self.index_name)

    # Record with middle initial matching voter should have better score
    middle_name_initial_score = match_one(
        search_type=SEARCH_TYPE_DISCOVER,
        first_name='Sappirole',
        middle_name='D',
        last_name='Fragmenter',
        index=self.index_name)['_debug_score']
    no_middle_name_score = match_one(
        search_type=SEARCH_TYPE_DISCOVER,
        first_name='Sappirole',
        last_name='Fragmenter',
        index=self.index_name)['_debug_score']

    self.assertGreater(middle_name_initial_score, no_middle_name_score)

  def test_middle_name_initial_query_score(self):
    match = fake_voter(first_name='Lampertman',
                       last_name='Shrampton',
                       middle_name='F',
                       dob=date(1980, 1, 1))

    index_fake_voters([match], self.index_name)

    # Record with middle name starting with F should be first
    middle_name_score = match_one(
        search_type=SEARCH_TYPE_DISCOVER,
        first_name='Lampertman',
        middle_name='Frankter',
        last_name='Shrampton',
        index=self.index_name)['_debug_score']
    no_middle_name_score = match_one(
        search_type=SEARCH_TYPE_DISCOVER,
        first_name='Lampertman',
        last_name='Shrampton',
        index=self.index_name)['_debug_score']

    self.assertGreater(middle_name_score, no_middle_name_score)

  def test_middle_name_query_score(self):
    match = fake_voter(first_name='Genghis',
                       middle_name='Herbert',
                       last_name='Khan',
                       dob=date(1980, 1, 1))

    index_fake_voters([match], self.index_name)

    # Record with middle name hit should be first
    middle_name_score = match_one(
        search_type=SEARCH_TYPE_DISCOVER,
        first_name='Genghis',
        middle_name='Herbert',
        last_name='Khan',
        index=self.index_name)['_debug_score']
    no_middle_name_score = match_one(
        search_type=SEARCH_TYPE_DISCOVER,
        first_name='Genghis',
        last_name='Khan',
        index=self.index_name)['_debug_score']

    self.assertGreater(middle_name_score, no_middle_name_score)

  def test_by_alternative_name(self):
    match = fake_voter(first_name='John',
                       middle_name='Calvin',
                       last_name='Coolidge Jr',
                       dob=date(1923, 10, 1))

    index_fake_voters([match], self.index_name)

    # There should not be a verification based on name only
    alternative_name = match_many(
        search_type=SEARCH_TYPE_DISCOVER,
        first_name='Edwardo',
        last_name='Wrongperson',
        alternative_first_name='Calvin',
        alternative_last_name='Coolidge',
        dob=date(1923, 10, 1),
        index=self.index_name)

    eq_(alternative_name[0]['id'], match['id'])

  def test_middle_name_extraction(self):
    match = fake_voter(first_name='Barack',
                       middle_name='Hussein',
                       last_name='Obama',
                       dob=date(1961, 8, 4))

    index_fake_voters([match], self.index_name)

    middle_in_first = match_many(
        search_type=SEARCH_TYPE_AUTO_VERIFY,
        first_name='Barack Hussein',
        last_name='Obama',
        dob=date(1961, 8, 4),
        index=self.index_name)
    eq_(middle_in_first[0]['id'], match['id'])

    initial_in_first = match_many(
        search_type=SEARCH_TYPE_AUTO_VERIFY,
        first_name='Barack H.',
        last_name='Obama',
        dob=date(1961, 8, 4),
        index=self.index_name)
    eq_(initial_in_first[0]['id'], match['id'])

    middle_in_last = match_many(
        search_type=SEARCH_TYPE_AUTO_VERIFY,
        first_name='Barack',
        last_name='Hussein Obama',
        dob=date(1961, 8, 4),
        index=self.index_name)
    eq_(middle_in_last[0]['id'], match['id'])

    initial_in_last = match_many(
        search_type=SEARCH_TYPE_AUTO_VERIFY,
        first_name='Barack',
        last_name='H. Obama',
        dob=date(1961, 8, 4),
        index=self.index_name)
    eq_(initial_in_last[0]['id'], match['id'])

  def test_compact_name(self):
    match = fake_voter(first_name="De'Quan",
                       middle_name="O'Brien",
                       last_name="da'Silva",
                       dob=date(1923, 10, 1))

    index_fake_voters([match], self.index_name)

    # Find the person based on all names with apostrophes.
    with_apostrophe = match_many(
        search_type=SEARCH_TYPE_DISCOVER,
        first_name="De'Quan",
        middle_name="O'Brien",
        last_name="da'Silva",
        dob=date(1923, 1, 1),
        index=self.index_name)
    eq_(with_apostrophe[0]['id'], match['id'])

    # Find the person based on all names without apostrophes.
    without_apostrophe = match_many(
        search_type=SEARCH_TYPE_DISCOVER,
        first_name="Dequan",
        middle_name="OBrien",
        last_name="da silva",
        dob=date(1923, 1, 1),
        index=self.index_name)
    eq_(without_apostrophe[0]['id'], match['id'])

  def test_auto_verification_unique_name(self):
    fake_voter_zip = '94708'
    location_for_zip_code = zip_to_lat_lng.get_lat_lng_str(fake_voter_zip)
    match = fake_voter(first_name='Jimmy',
                       last_name='Carter',
                       dob=date(1924, 10, 1),
                       zip_code=fake_voter_zip,
                       lat_lng_location=location_for_zip_code)

    index_fake_voters([match], self.index_name)

    # There should not be a verification based on name only
    auto_verify_without_dob_or_zip = match_many(
        search_type=SEARCH_TYPE_AUTO_VERIFY,
        first_name='Jimmy',
        last_name='Carter',
        index=self.index_name)
    eq_(len(auto_verify_without_dob_or_zip), 0)

    # Since there are no other people with similar name and DoB, verify.
    auto_verify_with_dob_only = match_many(
        search_type=SEARCH_TYPE_AUTO_VERIFY,
        first_name='Jimmy',
        last_name='Carter',
        dob=date(1924, 10, 1),
        index=self.index_name)
    eq_(len(auto_verify_with_dob_only), 1)

    # Exact match on zipcode is enough, even without DoB
    auto_verify_with_dob_and_zip = match_many(
        search_type=SEARCH_TYPE_AUTO_VERIFY,
        first_name='Jimmy',
        last_name='Carter',
        zip_code=fake_voter_zip,
        index=self.index_name)
    eq_(len(auto_verify_with_dob_and_zip), 1)

    # Zip does not match, but is very close. Verify.
    near_by_zip = '94707'
    auto_verify_with_dob_and_zip = match_many(
        search_type=SEARCH_TYPE_AUTO_VERIFY,
        first_name='Jimmy',
        last_name='Carter',
        zip_code=near_by_zip,
        index=self.index_name)
    eq_(len(auto_verify_with_dob_and_zip), 1)

    # Zip is not close enough. Do not verify based on this.
    far_away_zip = '11215'
    auto_verify_with_dob_and_zip = match_many(
        search_type=SEARCH_TYPE_AUTO_VERIFY,
        first_name='Jimmy',
        last_name='Carter',
        zip_code=far_away_zip,
        index=self.index_name)
    eq_(len(auto_verify_with_dob_and_zip), 0)

  def test_auto_verification_common_name(self):
    fake_voter_zip = '94708'
    location_for_zip_code = zip_to_lat_lng.get_lat_lng_str(fake_voter_zip)
    match = fake_voter(first_name='Ronald',
                       last_name='Reagan',
                       address="7 Tear down that wall St",
                       city="Bestville",
                       st="CA",
                       dob=date(1911, 1, 1), # Only year is indexed
                       zip_code=fake_voter_zip,
                       lat_lng_location=location_for_zip_code)
    far_away_zip = '11215'
    location_for_far_away_zip = zip_to_lat_lng.get_lat_lng_str(far_away_zip)
    index_fake_voters([
        # Voter in the same zip, but different DoB
        fake_voter(first_name='Ronald',
                   last_name='Reagan',
                   dob=date(1975, 12, 3),
                   zip_code=fake_voter_zip,
                   lat_lng_location=location_for_zip_code),
        # Voter born in the same year, but is far away. Note that the fact
        # that the DoB does not match is not known, as the index only has
        # year (month and day are both 1)
        fake_voter(first_name='Ronald',
                   last_name='Reagan',
                   dob=date(1911, 2, 1),
                   zip_code=far_away_zip,
                   lat_lng_location=location_for_far_away_zip),
        # year (month and day are both 1)
        fake_voter(first_name='Ronald',
                   last_name='Reagan',
                   dob=date(1911, 2, 1),
                   zip_code=far_away_zip,
                   lat_lng_location=location_for_far_away_zip),
         match]
    , self.index_name)

    # When providing an exact zip and dob, verify.
    auto_verify = match_many(
        search_type=SEARCH_TYPE_AUTO_VERIFY,
        first_name='Ronald',
        last_name='Reagan',
        dob=date(1911, 2, 6), # correct DoB
        zip_code=fake_voter_zip,
        index=self.index_name)
    eq_(len(auto_verify), 1)
    eq_(auto_verify[0]['id'], match['id'])
    self.assertTrue(auto_verify[0]['auto_verify'])

    close_enough_zip = '94707'
    # When providing close enough zip and dob, verify
    auto_verify = match_many(
        search_type=SEARCH_TYPE_AUTO_VERIFY,
        first_name='Ronald',
        last_name='Reagan',
        dob=date(1911, 2, 6), # correct DoB
        zip_code=close_enough_zip,
        index=self.index_name)
    eq_(len(auto_verify), 1)
    eq_(auto_verify[0]['id'], match['id'])
    self.assertTrue(auto_verify[0]['auto_verify'])

    # When providing correct zip, but clearly wrong dob, do not verify
    auto_verify = match_many(
        search_type=SEARCH_TYPE_AUTO_VERIFY,
        first_name='Ronald',
        last_name='Reagan',
        dob=date(1935, 2, 6), # correct DoB
        zip_code=fake_voter_zip,
        index=self.index_name)
    self.assertTrue(len(auto_verify) == 0 or
        (not auto_verify[0]['auto_verify'] and len(auto_verify) > 1))

  def test_auto_verification_based_on_exact_address(self):
    fake_voter_zip = '94708'
    location_for_zip_code = zip_to_lat_lng.get_lat_lng_str(fake_voter_zip)
    match = fake_voter(first_name='William',
                       middle_name='Jefferson',
                       last_name='Clinton',
                       address="7 I did not st",
                       city="Clintonia",
                       st="CA",
                       dob=date(1946, 1, 1), # Only year is indexed
                       zip_code=fake_voter_zip,
                       lat_lng_location=location_for_zip_code)
    index_fake_voters([
        fake_voter(first_name='Will',
                   last_name='Clinton',
                   address="98 Different Dude Ave",
                   city="Clintonia",
                   st="CA",
                   dob=date(1946, 1, 1), # Only year is indexed, same year
                   zip_code=fake_voter_zip,
                   lat_lng_location=location_for_zip_code),
        match], self.index_name)

    # In this case, it is too risky to verify based on zip alone
    # (2 people same year)
    auto_verify = match_many(
        search_type=SEARCH_TYPE_AUTO_VERIFY,
        first_name='Bill',
        last_name='Clinton',
        dob=date(1946, 8, 19), # correct DoB
        zip_code=fake_voter_zip,
        index=self.index_name)
    self.assertTrue(len(auto_verify) == 0 or
        (not auto_verify[0]['auto_verify'] and len(auto_verify) > 1))

    # Using Tower data, we might get exact address match, in that case, verify
    auto_verify = match_many(
        search_type=SEARCH_TYPE_AUTO_VERIFY,
        first_name='Bill',
        last_name='Clinton',
        dob=date(1946, 8, 19), # correct DoB
        zip_code=fake_voter_zip,
        address="7 I did not st",
        city="Clintonia",
        state="CA",
        index=self.index_name)
    eq_(len(auto_verify), 1)
    eq_(auto_verify[0]['id'], match['id'])
    self.assertTrue(auto_verify[0]['auto_verify'])

  def test_first_name_filter(self):
    fake_voter_zip = '94708'
    location_for_zip_code = zip_to_lat_lng.get_lat_lng_str(fake_voter_zip)
    match = fake_voter(first_name='Thomas',
                       middle_name='Woodrow',
                       last_name='Wilson',
                       dob=date(1956, 1, 1), # Only year and month are indexed
                       zip_code=fake_voter_zip,
                       lat_lng_location=location_for_zip_code)

    index_fake_voters([match], self.index_name)

    auto_verify = match_many(
        search_type=SEARCH_TYPE_AUTO_VERIFY,
        first_name='Kosmo',
        last_name='Wilson',
        dob=date(1955, 1, 1), # wrong year, correct month/day
        zip_code=fake_voter_zip,
        index=self.index_name)
    eq_(len(auto_verify), 0)

    top = match_many(
        search_type=SEARCH_TYPE_TOP,
        first_name='Kosmo',
        last_name='Wilson',
        dob=date(1957, 1, 1), # wrong year, correct month/day
        zip_code=fake_voter_zip,
        index=self.index_name)
    eq_(len(top), 0)

    discover = match_many(
        search_type=SEARCH_TYPE_DISCOVER,
        first_name='Kosmo',
        last_name='Wilson',
        dob=date(1955, 1, 1), # wrong year, correct month/day
        zip_code=fake_voter_zip,
        index=self.index_name)
    eq_(discover[0]['id'], match['id'])

    auto_verify = match_many(
        search_type=SEARCH_TYPE_AUTO_VERIFY,
        first_name='Woody',
        last_name='Wilson',
        dob=date(1955, 1, 1), # wrong year, correct month/day
        zip_code=fake_voter_zip,
        index=self.index_name)
    eq_(auto_verify[0]['id'], match['id'])

    top = match_many(
        search_type=SEARCH_TYPE_TOP,
        first_name='Woody',
        last_name='Wilson',
        dob=date(1957, 1, 1), # wrong year, correct month/day
        zip_code=fake_voter_zip,
        index=self.index_name)
    eq_(top[0]['id'], match['id'])

    discover = match_many(
        search_type=SEARCH_TYPE_DISCOVER,
        first_name='Woody',
        last_name='Wilson',
        dob=date(1957, 1, 1), # wrong year, correct month/day
        zip_code=fake_voter_zip,
        index=self.index_name)
    eq_(discover[0]['id'], match['id'])

  def test_top_type_search(self):
    fake_voter_zip = '94708'
    location_for_zip_code = zip_to_lat_lng.get_lat_lng_str(fake_voter_zip)
    match = fake_voter(first_name='Gerald',
                       middle_name='Rudolph',
                       last_name='Ford Jr.',
                       address="1 Our constitution works st",
                       city="Fordera",
                       st="MI",
                       dob=date(1913, 7, 1), # Only year and month are indexed
                       zip_code=fake_voter_zip,
                       lat_lng_location=location_for_zip_code)
    index_fake_voters([
        fake_voter(first_name='Gerald',
                   last_name='Ford',
                   dob=date(1913, 10, 12), # Only year is indexed, same year
                   zip_code=fake_voter_zip,
                   lat_lng_location=location_for_zip_code),
        fake_voter(first_name='Jerry',
                   last_name='Ford',
                   dob=date(1956, 10, 12), # Only year is indexed, same year
                   zip_code=fake_voter_zip,
                   lat_lng_location=location_for_zip_code),
        fake_voter(first_name='Gerald',
                   last_name='Ford',
                   dob=date(1922, 8, 10), # Only year is indexed, same year
                   zip_code=fake_voter_zip,
                   lat_lng_location=location_for_zip_code),
        fake_voter(first_name='Gerald',
                   last_name='Ford-Focus',
                   dob=date(1977, 6, 29), # Only year is indexed, same year
                   zip_code=fake_voter_zip,
                   lat_lng_location=location_for_zip_code),
        match], self.index_name)

    # In this case, it is too risky to verify based on zip alone
    # (2 people same year)
    auto_verify = match_many(
        search_type=SEARCH_TYPE_AUTO_VERIFY,
        first_name='Jerry',
        last_name='Ford',
        dob=date(1913, 1, 1), # correct DoB
        index=self.index_name)
    self.assertTrue(len(auto_verify) == 0 or
        (not auto_verify[0]['auto_verify'] and len(auto_verify) > 1))

    # Using TOP, this should be enough for showing user a result
    auto_verify = match_many(
        search_type=SEARCH_TYPE_TOP,
        first_name='Jerry',
        last_name='Ford',
        dob=date(1913, 1, 1), # correct DoB
        index=self.index_name)
    self.assertGreater(len(auto_verify), 0)
    eq_(auto_verify[0]['id'], match['id'])

  def test_no_year_of_birth(self):
      fake_voter_zip = '94618'
      location_for_zip_code = zip_to_lat_lng.get_lat_lng_str(fake_voter_zip)
      match = fake_voter(first_name='Dent',
                         middle_name='Arthur',
                         last_name='Dent',
                         zip_code=fake_voter_zip,
                         lat_lng_location=location_for_zip_code)

      index_fake_voters([match], self.index_name)

      # query has a date of birth
      for stype in [SEARCH_TYPE_AUTO_VERIFY, SEARCH_TYPE_TOP, SEARCH_TYPE_DISCOVER]:
          hits = match_many(
              search_type=stype,
              first_name='Dent',
              last_name='Dent',
              dob=date(1933, 3, 22),
              zip_code=fake_voter_zip,
              index=self.index_name)
          eq_(hits[0]['id'], match['id'])

      # no dob in query either
      for stype in [SEARCH_TYPE_AUTO_VERIFY, SEARCH_TYPE_TOP, SEARCH_TYPE_DISCOVER]:
          hits = match_many(
              search_type=stype,
              first_name='Dent',
              last_name='Dent',
              zip_code=fake_voter_zip,
              index=self.index_name)
          eq_(hits[0]['id'], match['id'])

  def test_year_of_birth(self):
      fake_voter_zip = '94708'
      location_for_zip_code = zip_to_lat_lng.get_lat_lng_str(fake_voter_zip)
      match = fake_voter(first_name='James',
                         middle_name='Tiberius',
                         last_name='Kirk',
                         dob=date(1933, 3, 22),
                         zip_code=fake_voter_zip,
                         lat_lng_location=location_for_zip_code)

      index_fake_voters([match], self.index_name)

      for stype in [SEARCH_TYPE_AUTO_VERIFY, SEARCH_TYPE_TOP, SEARCH_TYPE_DISCOVER]:
          hits = match_many(
              search_type=stype,
              first_name='James',
              last_name='Kirk',
              dob=date(1931, 3, 22), # birth year must be within one year to match
              zip_code=fake_voter_zip,
              index=self.index_name)
          eq_(len(hits), 0)

      # year of birth within 1 year
      for stype in [SEARCH_TYPE_AUTO_VERIFY, SEARCH_TYPE_TOP, SEARCH_TYPE_DISCOVER]:
          for yob in [1932, 1933, 1934]:
              hits = match_many(
                  search_type=stype,
                  first_name='James',
                  last_name='Kirk',
                  dob=date(yob, 3, 22),
                  zip_code=fake_voter_zip,
                  index=self.index_name)
              eq_(hits[0]['id'], match['id'])

      # no date of birth in query
      for stype in [SEARCH_TYPE_AUTO_VERIFY, SEARCH_TYPE_TOP, SEARCH_TYPE_DISCOVER]:
          hits = match_many(
              search_type=stype,
              first_name='James',
              last_name='Kirk',
              zip_code=fake_voter_zip,
              index=self.index_name)
          eq_(hits[0]['id'], match['id'])


  @classmethod
  def teardown(self):
    es_client.delete_index(self.index_name)

def index_fake_voters(voters, index_name):
  """
  Index an iterable of voter dicts.

  The voters need not actually be in the DB. They must have either
  complete DOBs or entirely null ones.
  """
  ensure_mapping_exists(index_name, es_client)
  consume(index_voters(index_name, voters, es_client))

  # Make sure the tests can see what we just indexed:
  es_client.refresh(index_name)


ID_COUNTER = 1
EXACT_TRACK_COUNTER = 1


def fake_voter(**kwargs):
  """Return a voter map with the given field values and the rest arbitrary."""
  v = dict(first_name='',
           last_name='',
           middle_name='',
           suffix='',
           address='',
           ts_address='',
           city='',
           ts_city='',
           st='',
           ts_st='',
           zip_code='',
           ts_zip_code='',
           lat_lng_location='',
           ts_lat_lng_location='',
           dob=None,
           status_flag='A',
           party='Republican',
           registration_date=None,
           first_time_seen_voter_id=None,
           identifier_scope_id=None,
           identifier='',
           general_2014=False,
           general_2012=False,
           general_2010=False,
           general_2008=False,
           general_2006=False,
           general_2004=False,
           general_2002=False,
           general_2000=False)

  # limit kwargs to only those expected by the ES index
  valid_keys = v.keys()
  valid_keys.extend(['id'])
  valid_kwargs = dict(i for i in kwargs.items() if i[0] in valid_keys)
  v.update(valid_kwargs)

  # add poor man's auto counter as id if missing
  global ID_COUNTER
  if 'id' not in v:
    v['id'] = str(ID_COUNTER)
    ID_COUNTER += 1
  global EXACT_TRACK_COUNTER
  if 'ts_exact_track' not in v:
    v['ts_exact_track'] = str(EXACT_TRACK_COUNTER)
    EXACT_TRACK_COUNTER += 1

  # parse and split out dob parts
  dob = v['dob']
  if dob and not isinstance(dob, date):
    dob = parse(v['dob']).date()
    v['dob'] = dob
  v['dob_year'] = dob and dob.year
  v['dob_month'] = dob and dob.month
  v['dob_day'] = dob and dob.day
  v['address_street_name'] = 'SOMEWHERE DR'
  v['address_street_number'] = 123
  v['address_unit_designator'] = 'APT'
  v['address_apt_number'] = 1234
  v['first_name_compact'] = v['first_name']
  v['middle_name_compact'] = v['middle_name']
  v['last_name_compact'] = v['last_name']
  return v
