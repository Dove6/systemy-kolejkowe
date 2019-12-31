from api import get_office_list, get_matter_list, APIError
from gui import HiDpiApplication, MainWindow
from PyQt5.QtCore import QPointF


application = HiDpiApplication([])
window = MainWindow()

def combo_callback(item_index):
    window.killTimer()
    matter_list = get_matter_list(window.combo_box.itemData(item_index))
    window.chart.setSeriesCount(len(matter_list['result']['grupy']))
    for index, group in enumerate(matter_list['result']['grupy']):
        window.chart.series()[index] << QPointF(60, group['liczbaKlwKolejce'])
    window.startTimer(60000)

office_list = sorted(get_office_list(), key=lambda x: x['name'])
window.combo_box.setItems([x['name'] for x in office_list], [x['id'] for x in office_list])
window.combo_box.currentIndexChanged.connect(combo_callback)

window.show()
application.exec_()
window.killTimer()

# console/test part
print('[LISTA URZĘDÓW]')
for index, office in enumerate(map(lambda x: x['name'], office_list)):
    print(f'{index + 1}. {office}')
print('\nWybierz numer urzędu:')
chosen_one = int(input()) - 1
if chosen_one > len(office_list) or chosen_one < 0:
    print('Numer niepoprawny!')
    exit()

print('\nWybrany urząd:', office_list[chosen_one]['name'])
try:
    data = get_matter_list(office_list[chosen_one]['id'])
except APIError as e:
    print('[BŁĄD]')
    print(e)
    exit()

print('[LISTA SPRAW]')
for index, task in enumerate(map(lambda x: x['nazwaGrupy'], data['result']['grupy'])):
    print(f'{index + 1}. {task}')
