from datetime import date
from unittest import TestCase
from logging import INFO

from django.utils.datetime_safe import date as safe_date
from pyelasticsearch import ElasticSearch

from voter_verifier.indexing import _document_from_mapping, aliased_index
from voter_verifier.config import ES_HOSTS, TIMEOUT, RETRIES, INDEX


es_client = ElasticSearch(ES_HOSTS, TIMEOUT, RETRIES)
es_client.logger.setLevel(INFO)


def voter_with_unknown_dob(**kwargs):
  """
  Return a voter mapping where dob_year, dob_month, and dob_day have expected
  values for good dates.

  For bad dates, set the attrs yourself; there's no way to represent a bad
  date to stick in the dob field.
  """
  v = dict(first_name='Fred',
           last_name='Finster',
           middle_name='Jack',
           suffix='',
           address='',
           city='',
           st='CA',
           zip_code='94085',
           dob=None,
           status_flag='A',
           identifier_scope_id=None,
           identifier='smoo')
  v.update(kwargs)
  v['dob_year'] = v['dob'] and v['dob'].year
  v['dob_month'] = v['dob'] and v['dob'].month
  v['dob_day'] = v['dob'] and v['dob'].day
  return v


class DayOfYearTests(TestCase):
  """Tests for the indexing of the day-ordinal number on voters"""

  def test_partial(self):
    """If day or month are unknown, don't try to compute the ordinal."""
    v = voter_with_unknown_dob(dob=None)
    v['dob_year'] = 1984
    v['dob_month'] = 4
    v['dob_day'] = 0
    doc = _document_from_mapping(v)
    self.assertFalse('dob_day_of_year' in doc)

  def test_partial(self):
    """If day and month are known, get the ordinal right."""
    doc = _document_from_mapping(
        voter_with_unknown_dob(dob=date(1970, 2, 3)))
    self.assertEqual(doc['dob_day_of_year'], 34)

  def test_february_29(self):
    """Test the special-casing for 2/29."""
    doc = _document_from_mapping(
        voter_with_unknown_dob(dob=date(2004, 2, 29)))
    self.assertEqual(doc['dob_day_of_year'], 60)


class IdentifierTests(TestCase):
  """Tests for indexing of the registrar-provided voter ID"""

  def test_scope_id(self):
    """Make sure identifier scope ID gets onto the document."""
    doc = _document_from_mapping(voter_with_unknown_dob(
        identifier_scope_id=33))
    self.assertEqual(doc['identifier_scope_id'], 33)

  def test_scope_and_identifier(self):
    """Make sure the combined scope-and-ID value gets onto the document."""
    doc = _document_from_mapping(voter_with_unknown_dob(
        identifier_scope_id=33, identifier='ABCD'))
    self.assertEqual(doc['scope_and_identifier'], '33 ABCD')

  def test_null(self):
    """If scope and identifier are null, don't index them."""
    doc = _document_from_mapping(voter_with_unknown_dob(
        identifier_scope=None, identifier=None))
    self.assertFalse('scope_and_identifier' in doc)


class IndexAliasTests(TestCase):
  """ Tests ensuring that the alias switchover works as intended """

  def test_switchover_when_index_does_not_exist(self):
    dest_index = 'test_voter_verifier_alias'

    try:
      es_client.delete_index(dest_index)
    except:
      pass

    with aliased_index(es_client, dest_index) as index:
      es_client.index(index, 'test', doc={'foo': 'bar'})

    es_client.refresh(index)

    query = {"query": {"match": {"foo": "bar"}}}
    results = es_client.search(query, index=dest_index)
    self.assertEqual(results['hits']['total'], 1)

  def test_switchover_twice(self):
    dest_index = 'test_voter_verifier_alias'

    try:
      ensure_mapping_exists(dest_index, es_client, force_delete=True)
    except:
      pass

    with aliased_index(es_client, dest_index) as index:
      es_client.index(index, 'test', doc={'abc': 'def'})

    es_client.refresh(dest_index)
    query = {"query": {"match": {"abc": "def"}}}
    results = es_client.search(query, index=dest_index)
    self.assertEqual(results['hits']['total'], 1)

    with aliased_index(es_client, dest_index) as index:
      es_client.index(index, 'test', doc={'ghi': 'jkl'})

    es_client.refresh(dest_index)
    query = {"query": {"match": {"abc": "def"}}}
    results = es_client.search(query, index=dest_index)
    self.assertEqual(results['hits']['total'], 0)

    query = {"query": {"match": {"ghi": "jkl"}}}
    results = es_client.search(query, index=dest_index)
    self.assertEqual(results['hits']['total'], 1)
