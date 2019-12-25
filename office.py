from html.parser import HTMLParser
from urllib.request import urlopen


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
                    self._offices.append({'name': None, 'id': attrs['id']})
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


def get_office_list():
    url = 'https://api.um.warszawa.pl/daneszcz.php?data=16c404ef084cfaffca59ef14b07dc516'
    request = urlopen(url)
    response = request.read().decode('utf-8')
    parser = OfficeListParser()
    return parser.feed(response)
