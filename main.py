from office import get_office_list
from urllib.request import urlopen
from urllib.parse import urlencode
import json


def append_parameters(url, params):
    if '?' in url:
        if '=' in url:
            url += '&'
    else:
        url += '?'
    url += urlencode(params)
    return url


base_url = 'https://api.um.warszawa.pl/api/action/wsstore_get/'
with open('apikey') as apikey:
    parameters = {
        'id': '',
        'apikey': apikey.read().strip()
    }
office_list = sorted(get_office_list(), key=lambda x: x['name'])

print('[LISTA URZĘDÓW]')
for index, office in enumerate(map(lambda x: x['name'], office_list)):
    print(f'{index + 1}. {office}')
print('\nWybierz numer urzędu:')
chosen_one = int(input()) - 1
if chosen_one > len(office_list) or chosen_one < 0:
    print('Numer niepoprawny!')
    exit()

print('\nWybrany urząd:', office_list[chosen_one]['name'])
parameters['id'] = office_list[chosen_one]['id']
request = urlopen(append_parameters(base_url, parameters))
response = request.read().decode('utf-8').strip()
data = json.loads(response)
if data['result'] == 'false':
    print('[BŁĄD]')
    print(data['error'])
    exit()

print('[LISTA SPRAW]')
for index, task in enumerate(map(lambda x: x['nazwaGrupy'], data['result']['grupy'])):
    print(f'{index + 1}. {task}')
