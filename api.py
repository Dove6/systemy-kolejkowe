from html.parser import HTMLParser
from urllib.request import urlopen
from urllib.parse import urlencode
import json


class OfficeListParser(HTMLParser):

    def __init__(self):
        super().__init__()
        self._found_id = False
        self._awaiting_name = False
        self._offices = []

    def handle_starttag(self, tag, attrs):
        sought = {
            'class': 'show_example',
            'role': 'wsstore_api_info#https://api.um.warszawa.pl/api/action'
        }
        if tag == 'div':
            attrs = dict(attrs)
            if set(['role', 'class', 'id']).issubset(set(attrs.keys())):
                if attrs['class'] == sought['class'] and attrs['role'] == sought['role']:
                    self._offices.append({'name': None, 'key': attrs['id']})
                    self._found_id = True

    def handle_data(self, data):
        data = data.strip()
        if data != '':
            if self._awaiting_name:
                self._offices[len(self._offices) - 1]['name'] = data
                self._found_id = False
                self._awaiting_name = False
            elif self._found_id:
                if data == 'Opis danych':
                    self._awaiting_name = True

    def handle_endtag(self, tag):
        pass  # do nothing

    def handle_startendtag(self, tag, attrs):
        pass  # do nothing

    def feed(self, data):
        super().feed(data)
        return self._offices


class APIError(Exception):
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

    def get_office_list(self) -> list:
        request = urlopen(self._urls['html'], timeout=2)
        response = request.read().decode('utf-8')
        parser = OfficeListParser()
        return parser.feed(response)

    def get_matter_list(self, office_key: str) -> list:
        with open('apikey') as apikey:
            parameters = {
                'id': office_key,
                'apikey': apikey.read().strip()
            }
        request = urlopen(append_parameters(self._urls['json'], parameters), timeout=2)
        response = request.read().decode('utf-8').strip()
        data = json.loads(response)
        if data['result'] == 'false':
            raise APIError(data['error'])
        return [{
            'name': str(group['nazwaGrupy']),
            'ordinal': int(group['lp']) if group['lp'] is not None else None,
            'group_id': int(group['idGrupy']),
            'queue_length': int(group['liczbaKlwKolejce']),
            'open_counters': int(group['liczbaCzynnychStan']),
            'current_number': str(group['aktualnyNumer']),
            'time': str(data['result']['date'] + ' ' + data['result']['time'])
        }
            for group in data['result']['grupy']
        ]
