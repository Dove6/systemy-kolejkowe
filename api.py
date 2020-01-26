from html.parser import HTMLParser
from urllib.request import urlopen
from urllib.parse import urlencode
from urllib.error import URLError
import socket
import json

from typing import Union, Optional, Dict, List, Tuple, Any
from retrying import retry

OfficeData = Dict[str, str]
OfficeList = List[OfficeData]
MatterSampleData = Dict[str, Union[str, Optional[int]]]
MatterSampleList = List[MatterSampleData]


class OfficeListParser(HTMLParser):
    '''
    HTMLParser subclass that retrieves list of offices in a form of list of
    dictionaries.

    :ivar _flags: Flags used throughout the parsing/search process
    :ivar _office_list: Result of parsing stored internally
    '''
    def __init__(self) -> None:
        '''
        Initialize and reset this instance.
        '''
        super().__init__()
        self._flags: Dict[str, bool] = {
            'id_found': False,
            'awaiting_name': False
        }
        self._office_list: List[Dict[str, str]] = []

    def handle_starttag(
            self, tag: str, attrs: List[Tuple[str, str]]) -> None:
        '''
        Handle HTML starting tag occurence.
        (overriden callback function)

        :param tag: HTML starting tag name
        :param attrs: HTML starting tag attributes (key, value) pairs list
        '''
        # HTML tag attributes values of a tag containing office ID key
        sought_attrs = {
            'class': 'show_example',
            'role': 'wsstore_api_info#https://api.um.warszawa.pl/api/action'
        }
        # Desired data resides inside <div> tag: check only them
        if tag == 'div':
            attrs = dict(attrs)
            # Prepare subdictionary for comparing with sought_attrs
            checked_attrs = {
                key: attrs.get(key)
                for key in sought_attrs.keys()
                if attrs.get(key) is not None
            }
            # If attributes values match, increment parsing progress indicator
            # by modifying result and setting relevant flag
            if sought_attrs == checked_attrs:
                self._office_list.append({'name': None, 'key': attrs['id']})
                self._flags['id_found'] = True

    def handle_data(self, data: str) -> None:
        '''
        Handle HTML arbitrary data occurence.
        (overriden callback function)

        :param data: Arbitrary data (text node or script)
        '''
        data = data.strip()
        if data != '':
            if self._flags['awaiting_name']:
                # If office name text node is expected, finish office entry
                # processing and reset flags
                self._office_list[len(self._office_list) - 1]['name'] = data
                self._flags['id_found'] = False
                self._flags['awaiting_name'] = False
            elif self._flags['id_found']:
                # If office entry processing has been just started, seek for
                # office name occurence indicator. If found, set appropriate
                # flag
                if data == 'Opis danych':
                    self._flags['awaiting_name'] = True

    def handle_endtag(self, tag: str) -> None:
        '''
        Handle HTML ending tag occurence.
        (overriden callback function)

        Since nothing is needed to do here, the method does nothing.

        :param tag: HTML ending tag name
        '''
        pass

    def handle_startendtag(
            self, tag: str, attrs: List[Tuple[str, str]]) -> None:
        '''
        Handle XHTML-style empty tag occurence.
        (overriden callback function)

        Since nothing needs to be done here, the method does nothing.

        :param tag: HTML tag name
        :param attrs: HTML tag attributes (key, value) pairs list
        '''
        pass

    def reset(self) -> None:
        '''
        Reset parsing process.
        (overriden function)
        '''
        super().reset()
        self._office_list = []

    def get_result(self) -> List[Dict[str, str]]:
        '''
        Get the result of parsing.

        It explicitly closes the parsing process before fetching result

        :returns: Result office list
        '''
        self.close()
        return self._office_list[:]


def append_parameters(url: str, params: Dict[str, str]) -> str:
    '''
    Encode and append query parameters to an URL.

    :param url: Subject URL (may already contain query string)
    :param params: Query parameters to be appended
    :returns: Resulting URL
    '''
    # URL query string begins after the first question mark (if present)
    query_beginning = url.find('?')
    url_before_query = ''
    url_after_query = ''
    query_string = ''
    if query_beginning == -1:
        # URL without query string: append question mark separator
        url_before_query = url + '?'
    else:
        url_before_query = url[:query_beginning + 1]
        # URL query string ends before a hash mark (if present)
        query_ending = url.find('#', query_beginning + 1)
        if query_ending == -1:
            query_string = url[query_beginning + 1:]
        else:
            query_string = url[query_beginning + 1:query_ending]
            url_after_query = url[query_ending:]
        if query_string != '':
            # URL containing non-empty query string: append ampersand
            # delimiter
            query_string += '&'
    return (
        url_before_query + query_string + urlencode(params) + url_after_query)


class APIError(Exception):
    '''
    Exception indicating errors during fetching API data.
    '''
    pass


class APIConnectionError(APIError):
    '''
    Exception indicating errors during sending API request.
    '''
    pass


class APIResponseError(APIError):
    '''
    Exception indicating unexpected API response.
    '''
    pass


def is_connection_error(exception) -> bool:
    '''
    Check if provided exception is related to connecting to API.
    '''
    return isinstance(exception, APIConnectionError)


class WSStoreAPI:
    '''
    Class used for fetching queue system data using API provided by the City
    of Warsaw.

    :param html_api_url: Base URL of API returning HTML encoded data
    :param json_api_url: Base URL of API returning JSON encoded data
    :ivar _api_urls: Base URLs of APIs provided in constructor
    :ivar _office_key: Default office identifier (settable through
        self.office_key property)
    '''
    def __init__(self, html_api_url: str, json_api_url: str) -> None:
        self._api_urls: Dict[str, str] = {
            'html': html_api_url,
            'json': json_api_url
        }
        self._office_key: Optional[str] = None

    #
    # Private methods used internally
    #

    @retry(
        retry_on_exception=is_connection_error,
        wait_fixed=2000,
        stop_max_attempt_number=5)
    def _get_json_data(
            self, office_key: Optional[str] = None) -> Dict[str, Any]:
        '''
        Retrieve unprocessed office data from JSON API as a dictionary.
        (internal function)

        Function retries 5 times on connection errors, waiting 2 seconds
        between retries.

        :param office_key: Requested office identifier
            (defaults to self.office_key)
        :returns: Resulting dictionary
        :raises:
            :class:`AssertionError`: Missing argument
            :class:`APIConnectionError`: Error connecting to the API
            :class:`APIResponseError`: Unexpected response from the API
        '''
        if office_key is None:
            office_key = self._office_key
        # Check argument's validity
        if office_key is None:
            raise AssertionError('Office key not provided')
        from apikey import apikey
        # Prepare HTTP request GET parameters
        parameters = {
            'id': office_key,
            'apikey': apikey().strip()
        }
        # Make a HTTP request for fetching JSON data
        try:
            request = urlopen(
                append_parameters(self._api_urls['json'], parameters),
                timeout=5)
            response = request.read().decode('utf-8').strip()
        except (URLError, socket.timeout, socket.gaierror):
            raise APIConnectionError('Cannot connect to the API')
        # Parse fetched data
        data = json.loads(response)
        # Raise an error if API returned error response
        if type(data['result']) == str:
            if data.get('error') is not None:
                raise APIResponseError(data['error'])
            else:
                raise APIResponseError(data['result'])
        return data

    #
    # Public methods
    #

    @retry(
        retry_on_exception=is_connection_error,
        wait_fixed=2000,
        stop_max_attempt_number=5)
    def get_office_list(self) -> OfficeList:
        '''
        Retrieve office identifiers list from HTML API

        The list can be used to get office-specific data using the JSON API.

        Function retries 5 times on connection errors, waiting 2 seconds
        between retries.

        :returns: Office identifiers list
        :raises: :class:`APIConnectionError`: Error connecting to the API
        '''
        # Make a HTTP request for fetching HTML data
        try:
            request = urlopen(self._api_urls['html'], timeout=5)
            response = request.read().decode('utf-8')
        except (URLError, socket.timeout, socket.gaierror):
            raise APIConnectionError('Cannot connect to the API')
        # Parse fetched data
        parser = OfficeListParser()
        parser.feed(response)
        return parser.get_result()

    def get_matters_with_samples(
            self, office_key: Optional[str] = None) -> MatterSampleList:
        '''
        Retrieve office-specific list of current states of queues for each
        administrative matter available in the office using the JSON API.

        :param office_key: Requested office identifier
            (defaults to self._office_key)
        :returns: List of dictionaries describing each matter and its queue
            state
        '''
        # Fetch and parse JSON data
        data = self._get_json_data(office_key)
        # Parse and reorganize data according to internal data format
        return sorted([{
            'name': str(group['nazwaGrupy']),
            'ordinal': int(group['lp']) if group['lp'] is not None else None,
            'group_id': int(group['idGrupy']),
            'queue_length': int(group['liczbaKlwKolejce']),
            'open_counters': int(group['liczbaCzynnychStan']),
            'current_number': str(group['aktualnyNumer']),
            'time': str(data['result']['date'] + ' ' + data['result']['time'])
        }
            for group in data['result']['grupy']
        ], key=lambda matter: matter['name'])

    #
    # Properties
    #

    @property
    def office_key(self) -> str:
        '''
        Default office identifier used when per-method optional office key
        is not provided.

        :raises: :class:`TypeError`: Trying to assign non-string value
        '''
        return self._office_key

    @office_key.setter
    def office_key(self, value: str) -> None:
        if type(value) is str:
            self._office_key = value
        else:
            raise TypeError('Office key must be a string')
