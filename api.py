from html.parser import HTMLParser
from urllib.request import urlopen
from urllib.parse import urlencode
import json


class OfficeListParser(HTMLParser):
    '''
    HTMLParser subclass that retrieves list of offices in a form of list of
    dictionaries

    :ivar _flags: Flags used throughout the parsing/search process
    :vartype _flags: dict
    :ivar _sought_attrs: HTML tag attributes values indicating approaching
        occurence of office ID key
    :vartype _sought_attrs: dict
    :ivar _sought_tag: HTML tag name which attributes are to check
    :vartype _sought_tag: str
    :ivar _office_list: Result of parsing stored internally
    :vartype _office_list: list
    '''
    def __init__(self, *, **kwargs):
        super().__init__(**kwargs)
        self._flags = {
            'id_found': False,
            'awaiting_name': False
        }
        self._sought_attrs = {
            'class': 'show_example',
            'role': 'wsstore_api_info#https://api.um.warszawa.pl/api/action'
        }
        self._sought_tag = 'div'
        self._office_list = []

    def handle_starttag(self, tag, attrs):
        '''
        Overloaded internal function for handling HTML starting tag occurence

        :param tag: HTML starting tag name
        :type tag: str
        :param attrs: HTML starting tag attributes (key, value) pairs list
        :type attrs: list
        '''
        if tag == self._sought_tag:
            attrs = dict(attrs)
            # Preparing subdictionary for comparing with self._sought_attrs
            checked_attrs = {
                key: attrs.get(key)
                for key in self._sought_attrs.keys()
                if attrs.get(key) is not None
            }
            # If attributes values match, increment parsing progress indicator
            # by modifying result and setting relevant flag
            if self._sought_attrs == checked_attrs:
                self._offices.append({'name': None, 'key': attrs['id']})
                self._flags['id_found'] = True

    def handle_data(self, data):
        '''
        Overloaded internal function for handling HTML arbitrary data occurence

        :param data: Arbitrary data (text node or script)
        :type data: str
        '''
        data = data.strip()
        if data != '':
            # If office name text node is expected, finish office entry
            # processing and reset flags
            if self._flags['awaiting_name']:
                self._offices[len(self._offices) - 1]['name'] = data
                self._flags['id_found'] = False
                self._flags['awaiting_name'] = False
            # If office entry processing has been just started, seek for
            # office name occurence indicator. If found, set appropriate flag
            elif self._flags['id_found']:
                if data == 'Opis danych':
                    self._awaiting_name = True

    def handle_endtag(self, tag):
        '''
        Overloaded internal function for handling HTML ending tag occurence

        Since nothing is needed to do here, the method does nothing.

        :param tag: HTML ending tag name
        :type tag: str
        '''
        pass

    def handle_startendtag(self, tag, attrs):
        '''
        Overloaded internal function for handling XHTML-style empty tag
        occurence

        Since nothing is needed to do here, the method does nothing.

        :param tag: HTML tag name
        :type tag: str
        :param attrs: HTML tag attributes (key, value) pairs list
        :type attrs: list
        '''
        pass

    def reset(self):
        '''
        Overloaded public function for resetting parsing process
        '''
        super().reset()
        self._office_list = []

    def get_result(self):
        '''
        Getter function for getting result of parsing

        It explicitly closes the parsing process before fetching result

        :returns: Result office list
        :rtype: list
        '''
        self.close()
        return self._office_list[:]


class APIError(Exception):
    '''
    Exception indicating errors during fetching API data
    '''
    pass


def append_parameters(url: str, params: dict) -> str:
    if '?' in url:
        if '=' in url:
            url += '&'
    else:
        url += '?'
    url += urlencode(params)
    return url


class WSStoreAPI:
    def __init__(self, base_api_urls=None):
        if base_api_urls is not None:
            if not set(['html', 'json']).issubset(set(base_api_urls.keys())):
                raise AssertionError('Dictionary must contain "html" and "json" keys')
            self._urls = base_api_urls.copy()
        else:
            self._urls = None
        self._office_key = None

    def get_offices(self) -> list:
        request = urlopen(self._urls['html'], timeout=2)
        response = request.read().decode('utf-8')
        parser = OfficeListParser()
        parser.feed(response)
        return parser.get_result()

    def _get_json_data(self, office_key: str) -> dict:
        with open('apikey') as apikey:
            parameters = {
                'id': office_key,
                'apikey': apikey.read().strip()
            }
        request = urlopen(append_parameters(self._urls['json'], parameters), timeout=2)
        response = request.read().decode('utf-8').strip()
        data = json.loads(response)
        if type(data['result']) == str:
            if data.get('error') is not None:
                raise APIError(data['error'])
            else:
                raise APIError(data['result'])
        return data

    def get_matters_with_samples(self, office_key=None) -> list:
        if office_key is None:
            office_key = self._office_key
        data = self._get_json_data(office_key)
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

    @property
    def office_key(self):
        return self._office_key

    @office_key.setter
    def office_key(self, value):
        if type(value) is str:
            self._office_key = value
        else:
            raise TypeError('Office key must be a string')
