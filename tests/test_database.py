import pytest
import os
import sqlite3
from api import APIError
from database import SQLite3Cursor, DatabaseError, CachedAPI

#
# Testing the SQLite3Cursor context manager
#

@pytest.fixture
def remove_database_if_exists():
    '''
    Removes test database if it exists.
    '''
    if os.path.exists('tests/test.db'):
        os.remove('tests/test.db')

def test_cursor_context_basic():
    '''
    Test if cursor from context manager correctly returns data.
    '''
    with SQLite3Cursor(':memory:') as cursor:
        cursor.execute('SELECT 1')
        result = cursor.fetchall()
    assert isinstance(result, list)
    assert len(result) == 1
    assert isinstance(result[0], sqlite3.Row)
    assert len(result[0]) == 1
    assert result[0][0] == 1

def test_cursor_context_commit_data(remove_database_if_exists):
    '''
    Check, if cursor from context manager commits data on success.
    '''
    with SQLite3Cursor('tests/test.db') as cursor:
        cursor.execute(
            '''
            CREATE TABLE test (
                value INTEGER
            )
            ''')
    with SQLite3Cursor('tests/test.db') as cursor:
        cursor.execute('SELECT * FROM test')
        result = cursor.fetchall()
    assert isinstance(result, list)
    assert len(result) == 0

def test_cursor_context_rollback_data(remove_database_if_exists):
    '''
    Check, if cursor from context manager rollbacks data on error.
    '''
    with SQLite3Cursor('tests/test.db') as cursor:
        cursor.execute(
            '''
            CREATE TABLE test (
                value INTEGER
            )
            ''')
    try:
        with SQLite3Cursor('tests/test.db') as cursor:
            cursor.execute('INSERT INTO test VALUES (1)')
            raise Exception()
    except Exception:
        pass
    with SQLite3Cursor('tests/test.db') as cursor:
        cursor.execute('SELECT * FROM test')
        result = cursor.fetchall()
    assert isinstance(result, list)
    assert len(result) == 0

def test_cursor_context_custom_exception(remove_database_if_exists):
    '''
    Test, if the context manager converts database related exceptions
    to DatabaseError instances.
    '''
    with pytest.raises(DatabaseError):
        with SQLite3Cursor('tests/test.db') as cursor:
            cursor.execute('SELECT * FROM test')


#
# Testing the CachedAPI class
#

@pytest.fixture
def cached_api_instance():
    '''
    Returns CachedAPI instance using the prepared data from Pastebin
    and an empty test database.
    '''
    if os.path.exists('tests/test.db'):
        os.remove('tests/test.db')
    api_urls = {
        'html': 'https://pastebin.com/raw/jaQXNr23',
        'json': 'https://pastebin.com/raw/79W9hHcb'
    }
    return CachedAPI(api_urls['html'], api_urls['json'], 'tests/test.db')


def test_cached_api_table_structure(cached_api_instance):
    '''
    Check, if required tables are created.
    '''
    with SQLite3Cursor('tests/test.db') as cursor:
        # Non-existence of any table will throw an exception
        cursor.execute('SELECT * FROM offices')
        cursor.execute('SELECT * FROM matters')
        cursor.execute('SELECT * FROM samples')
        cursor.execute('SELECT * FROM last_connection')

def test_cached_api_html_result(cached_api_instance):
    '''
    Verify result's conformance to prepared HTML data.
    In case of exception, check its type.
    '''
    try:
        result = cached_api_instance.get_office_list()
        assert len(result) == 1
        assert isinstance(result[0], dict)
        assert list(result[0].keys()) == ['name', 'key']
        assert result[0]['name'] == 'Urząd Dzielnicy Wola'
        assert result[0]['key'] == '7ef70889-4eb9-4301-a970-92287db23052'
        with SQLite3Cursor('tests/test.db') as cursor:
            cursor.execute('SELECT * FROM offices')
            result = cursor.fetchall()
            assert len(result) == 1
            assert result[0]['name'] == 'Urząd Dzielnicy Wola'
            assert result[0]['key'] == '7ef70889-4eb9-4301-a970-92287db23052'
    except Exception as exc:
        assert isinstance(exc, APIError)

def test_cached_api_no_key_exception(cached_api_instance):
    '''
    Test if function correctly raises an exception when not provided with key
    identifier of JSON API interface.
    '''
    with pytest.raises(AssertionError, match='Office key'):
        cached_api_instance.get_matters_with_samples()

def test_cached_api_json_result(cached_api_instance):
    '''
    Verify result's conformance to prepared JSON data.
    In case of exception, check its type.
    '''
    cached_api_instance.office_key = ''
    with SQLite3Cursor('tests/test.db') as cursor:
        cursor.execute("INSERT INTO offices VALUES (1, 'test', '')")
        cursor.execute("INSERT INTO last_connection VALUES (1, NULL)")
    try:
        cached_api_instance.update()
        # Test matter list fetching
        result_matters = cached_api_instance.get_matter_list()
        assert isinstance(result_matters, list)
        assert len(result_matters) == 3
        assert isinstance(result_matters[0], dict)
        assert list(result_matters[0].keys()) == ['name', 'ordinal', 'group_id']
        with SQLite3Cursor('tests/test.db') as cursor:
            cursor.execute('SELECT * FROM matters ORDER BY name')
            db_result_matters = cursor.fetchall()
            assert len(db_result_matters) == 3
            assert db_result_matters[0]['office_id'] == 1
            assert db_result_matters[0]['name'] == result_matters[0]['name']
        # Test sample list fetching
        test_matter = result_matters[0]
        result_samples = cached_api_instance.get_sample_list(
            test_matter['ordinal'], test_matter['group_id'])
        assert isinstance(result_samples, list)
        # Check if samples should be available
        with SQLite3Cursor('tests/test.db') as cursor:
            cursor.execute(
                '''
                SELECT DATETIME(?, 'utc') < DATETIME('now', '-1 hour')
                ''', ('2019-12-27 15:41',))
            if cursor.fetchone()[0] == 1:
                hour_passed = True
            else:
                hour_passed = False
        if hour_passed:
            assert len(result_samples) == 0
            with SQLite3Cursor('tests/test.db') as cursor:
                cursor.execute(
                    '''
                    SELECT *
                    FROM samples JOIN matters
                    ON samples.matter_id = matters.id
                    WHERE ordinal = ? AND group_id = ?
                    ORDER BY time
                    ''', (test_matter['ordinal'], test_matter['group_id']))
                db_result_samples = cursor.fetchall()
                assert len(db_result_samples) == 0
        else:
            assert len(result_samples) == 1
            assert isinstance(result_samples[0], dict)
            assert list(result_samples[0].keys()) == [
                'queue_length', 'open_counters', 'current_number', 'time']
            with SQLite3Cursor('tests/test.db') as cursor:
                cursor.execute(
                    '''
                    SELECT *
                    FROM samples JOIN matters
                    ON samples.matter_id = matters.id
                    WHERE ordinal = ? AND group_id = ?
                    ORDER BY time
                    ''', (test_matter['ordinal'], test_matter['group_id']))
                db_result_samples = cursor.fetchall()
                assert len(db_result_samples) == 1
                assert db_result_samples[0]['time'] == '2019-12-27 15:41'
                assert db_result_samples[0]['queue_length'] == result_samples[0]['queue_length']
    except Exception as exc:
        assert isinstance(exc, APIError)
