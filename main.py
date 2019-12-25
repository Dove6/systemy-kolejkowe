from office import get_office_list
from urllib.request import urlopen
import json
from pprint import pprint


base_url = 'https://api.um.warszawa.pl/api/action/wsstore_get/?id='
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
request = urlopen(base_url + office_list[chosen_one]['id'])
response = request.read().decode('utf-8').strip()
data = json.loads(response)
if data['result'] == 'false':
    print('[BŁĄD]')
    print(data['error'])
    exit()

print('[LISTA SPRAW]')
for index, task in enumerate(map(lambda x: x['nazwaGrupy'], data['result']['grupy'])):
    print(f'{index + 1}. {task}')
