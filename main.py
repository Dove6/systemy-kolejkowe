from database import SQLite3Cursor, init_tables, get_office_list, get_matter_list
from api import APIError
from gui import HiDpiApplication, MainWindow
from PyQt5.QtWidgets import QTableWidgetItem
from PyQt5.QtCore import Qt, QPointF


with SQLite3Cursor('cache.db') as cursor:
    init_tables(cursor)
application = HiDpiApplication([])
window = MainWindow()


def combo_callback(item_index):
    window.killTimer()
    with SQLite3Cursor('cache.db') as cursor:
        matter_list = get_matter_list(cursor, window.combo_box.itemData(item_index))
    window.chart.setSeriesCount(len(matter_list['result']['grupy']))
    window.table.setRowCount(len(matter_list['result']['grupy']))
    for index, group in enumerate(matter_list['result']['grupy']):
        window.chart.series()[index] << QPointF(60, group['liczbaKlwKolejce'])
        window.table.setItem(index, 0, QTableWidgetItem(str(index + 1)))
        window.table.item(index, 0).setForeground(window.chart.series()[index].color())
        window.table.item(index, 0).setTextAlignment(Qt.AlignRight)
        window.table.setItem(index, 1, QTableWidgetItem(group['nazwaGrupy']))
        window.table.item(index, 1).setTextAlignment(Qt.AlignLeft)
        window.table.setItem(index, 2, QTableWidgetItem(str(group['liczbaCzynnychStan'])))
        window.table.item(index, 2).setTextAlignment(Qt.AlignCenter)
        window.table.setItem(index, 3, QTableWidgetItem(str(group['liczbaKlwKolejce'])))
        window.table.item(index, 3).setTextAlignment(Qt.AlignCenter)
        window.table.setItem(index, 4, QTableWidgetItem(group['aktualnyNumer']))
        window.table.item(index, 4).setTextAlignment(Qt.AlignCenter)
    window.startTimer(60000)


with SQLite3Cursor('cache.db') as cursor:
    office_list = sorted(get_office_list(cursor), key=lambda x: x['name'])
window.combo_box.setItems([x['name'] for x in office_list], [x['key'] for x in office_list])
window.combo_box.currentIndexChanged.connect(combo_callback)

window.show()
application.exec_()
exit()

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
