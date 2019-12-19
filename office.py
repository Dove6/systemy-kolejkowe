from html.parser import HTMLParser
from urllib.request import urlopen

class OfficeListParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self._in_tag = False
        self._offices = []
    def handle_starttag(self, tag, attrs):
        if tag == 'div':
            attrs = dict(attrs)
            if set(['role', 'class', 'id']).issubset(set(attrs.keys())):
                if attrs['class'] == 'show_example' and attrs['role'] == 'wsstore_api_info#https://api.um.warszawa.pl/api/action':
                    self._offices.append({'name': None, 'id': attrs['id']})
                    self._in_tag = True
    def handle_data(self, data):
        if self._in_tag:
            self._offices[len(self._offices) - 1]['name'] = data.strip()
    def handle_endtag(self, tag):
        if self._in_tag:
            self._in_tag = False
    def handle_startendtag(self, tag, attrs):
        pass
    def feed(self, data):
        super().feed(data)
        return self._offices


def get_office_list():
    url = 'https://api.um.warszawa.pl/daneszcz.php?data=16c404ef084cfaffca59ef14b07dc516'
    request = urlopen(url)
    response = request.read().decode('utf-8')
    parser = OfficeListParser()
    return parser.feed(response)
