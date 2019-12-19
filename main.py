from office import get_office_list
from urllib.request import urlopen


base_url = 'https://api.um.warszawa.pl/api/action/wsstore_get/?id='
office_list = get_office_list()

print('Wybierz urzęd, typie:')
for index, office in enumerate(map(lambda x: x['name'], office_list)):
    print(f'{index + 1}. {office}')

chosen_one = int(input()) - 1
if chosen_one > len(office_list) or chosen_one < 0:
    print('o ty')
    exit()

request = urlopen(base_url + office_list['id'])
response = request.read().decode('utf-8')
print(response)
