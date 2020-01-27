'''
Tests applying to api.py file.
'''
import pytest
from api import OfficeListParser, append_parameters, WSStoreAPI, APIError

#
# Testing the OfficeListParser class
#

@pytest.fixture
def office_list_parser():
    '''
    Returns OfficeListParser instance.
    '''
    return OfficeListParser()

@pytest.fixture
def fed_office_list_parser():
    '''
    Returns OfficeListParser instance fed with valid HTML data.
    '''
    with open('tests/test_response.html', 'rb') as test_file:
        test_html = test_file.read()
    test_html = test_html.decode('utf-8')
    parser = OfficeListParser()
    parser.feed(test_html)
    return parser


def test_parser_initial_result(office_list_parser):
    '''
    Test initial result of OfficeListParser. The result should be an empty
    list.
    '''
    assert office_list_parser.get_result() == []

def test_parser_result_empty_string(office_list_parser):
    '''
    Test result of OfficeListParser instance after feeding it with an empty
    string. Again, the result should be an empty list.
    '''
    office_list_parser.feed('')
    assert office_list_parser.get_result() == []

def test_parser_result_valid_data(fed_office_list_parser):
    '''
    Test result of OfficeListParser after feeding it with the prepared data.
    The resulting list should meet various criteria.
    '''
    office_list = fed_office_list_parser.get_result()
    assert len(office_list) == 1
    assert isinstance(office_list[0], dict)
    assert list(office_list[0].keys()) == ['name', 'key']
    assert office_list[0]['name'] == 'Urząd Dzielnicy Wola'
    assert office_list[0]['key'] == '7ef70889-4eb9-4301-a970-92287db23052'

def test_parser_result_reset(fed_office_list_parser):
    '''
    Test result of OfficeListParser instance after feeding it with the data
    and then resetting it. The result should be an empty list.
    '''
    fed_office_list_parser.reset()
    assert fed_office_list_parser.get_result() == []


#
# Testing the append_parameters function
#

def test_append_function_empty():
    '''
    Test providing the append_parameters function with empty arguments.
    The function should raise a ValueError because of empty URL.
    '''
    with pytest.raises(ValueError, match='No URL'):
        append_parameters('', {})

def test_append_function_params_without_url():
    '''
    Test providing the append_parameters function with empty URL and non-empty
    parameters dictionary. The function should raise a ValueError because of
    empty URL.
    '''
    with pytest.raises(ValueError, match='No URL'):
        append_parameters('', {'key1': 'value1', 'key2': 'value2'})

def test_append_function_params_without_params():
    '''
    Test providing the append_parameters function with an URL string and empty
    parameters dictionary. The function should return the same string.
    '''
    test_url = 'test.url/?'
    assert append_parameters(test_url, {}) == test_url

@pytest.mark.parametrize('url, params, expected_result', [
    ('test.url', {'key1': 'value1', 'key2': 'value2'},
     'test.url?key1=value1&key2=value2'),
    ('test.url?', {'key1': 'value1', 'key2': 'value2'},
     'test.url?key1=value1&key2=value2'),
    ('test.url?#hash', {'key1': 'value1', 'key2': 'value2'},
     'test.url?key1=value1&key2=value2#hash'),
    ('test.url/??', {'key1': 'value1', 'key2': 'value2'},
     'test.url/??&key1=value1&key2=value2'),
    ('test.url/?key0=value0', {'key1': 'value1', 'key2': 'value2'},
     'test.url/?key0=value0&key1=value1&key2=value2'),
    ('test.url/?key0=value0#hash', {'key1': 'value1', 'key2': 'value2'},
     'test.url/?key0=value0&key1=value1&key2=value2#hash'),
])
def test_append_function_url_and_params(url, params, expected_result):
    '''
    Test providing the append_parameters function with various non-empty data.
    The function should return the appropriate modified URL.
    '''
    assert append_parameters(url, params) == expected_result


#
# Testing the WSStoreAPI class
#

@pytest.fixture
def api_instance():
    '''
    Returns OfficeListParser instance using the prepared data from Pastebin.
    '''
    api_urls = {
        'html': 'https://pastebin.com/raw/jaQXNr23',
        'json': 'https://pastebin.com/raw/79W9hHcb'
    }
    return WSStoreAPI(api_urls['html'], api_urls['json'])


def test_api_html_result(api_instance):
    '''
    Verify result's conformance to prepared HTML data.
    In case of exception, check its type.
    '''
    try:
        result = api_instance.get_office_list()
        assert len(result) == 1
        assert isinstance(result[0], dict)
        assert list(result[0].keys()) == ['name', 'key']
        assert result[0]['name'] == 'Urząd Dzielnicy Wola'
        assert result[0]['key'] == '7ef70889-4eb9-4301-a970-92287db23052'
    except Exception as exc:
        assert isinstance(exc, APIError)

def test_api_no_key_exception(api_instance):
    '''
    Test if function correctly raises an exception when not provided with key
    identifier of JSON API interface.
    '''
    with pytest.raises(AssertionError, match='Office key'):
        api_instance.get_matters_with_samples()

def test_api_json_result(api_instance):
    '''
    Verify result's conformance to prepared JSON data.
    In case of exception, check its type.
    '''
    api_instance.office_key = ''
    try:
        result = api_instance.get_matters_with_samples()
        assert isinstance(result, list)
        assert len(result) == 3
        assert isinstance(result[0], dict)
        assert list(result[0].keys()) == [
            'name', 'ordinal', 'group_id', 'queue_length', 'open_counters', 'current_number', 'time']
    except Exception as exc:
        assert isinstance(exc, APIError)
