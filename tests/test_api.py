import pytest
from api import OfficeListParser, append_parameters

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
    with open('tests/test_office_list.html', 'rb') as test_file:
        test_html = test_file.read()
    test_html = test_html.decode('utf-8')
    parser = OfficeListParser()
    parser.feed(test_html)
    return parser

def test_parser_initial_result(office_list_parser):
    assert office_list_parser.get_result() == []

def test_parser_result_empty_string(office_list_parser):
    office_list_parser.feed('')
    assert office_list_parser.get_result() == []

def test_parser_result_valid_data(fed_office_list_parser):
    office_list = fed_office_list_parser.get_result()
    assert len(office_list) == 1
    assert isinstance(office_list[0], dict)
    assert list(office_list[0].keys()) == ['name', 'key']
    assert office_list[0]['name'] == 'Urząd Dzielnicy Wola'
    assert office_list[0]['key'] == '7ef70889-4eb9-4301-a970-92287db23052'

def test_parser_result_reset(fed_office_list_parser):
    fed_office_list_parser.reset()
    assert fed_office_list_parser.get_result() == []


#
# Testing the append_parameters function
#

def test_append_function_empty():
    assert append_parameters('', {}) == ''
