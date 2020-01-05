from database import CachedAPI
from api import APIError
from gui import HiDpiApplication, MainWindow
from PyQt5.QtWidgets import QTableWidgetItem
from PyQt5.QtCore import Qt, QPointF


api = CachedAPI({
    'html': 'https://api.um.warszawa.pl/daneszcz.php?data=16c404ef084cfaffca59ef14b07dc516',
    'json': 'https://api.um.warszawa.pl/api/action/wsstore_get/'
}, 'cache.db')

application = HiDpiApplication([])
window = MainWindow()


def combo_callback(item_index):
    window.timer.stop()
    try:
        matter_list = api.get_matter_list(window.combo_box.itemData(item_index))
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
        window.timer.start()
    except APIError as e:
        print('[BŁĄD]')
        print(e)
        exit()


def timer_callback():
    matter_list = api.get_matter_list(window.combo_box.currentData())
    for index, group in enumerate(matter_list['result']['grupy']):
        window.chart.series()[index].movePoints(-1)
        window.chart.series()[index] << QPointF(60, group['liczbaKlwKolejce'])
        window.table.item(index, 0).setText(str(index + 1))
        window.table.item(index, 1).setText(group['nazwaGrupy'])
        window.table.item(index, 2).setText(str(group['liczbaCzynnychStan']))
        window.table.item(index, 3).setText(str(group['liczbaKlwKolejce']))
        window.table.item(index, 4).setText(group['aktualnyNumer'])


office_list = sorted(api.get_office_list(), key=lambda x: x['name'])
window.combo_box.setItems([x['name'] for x in office_list], [x['key'] for x in office_list])
window.combo_box.currentIndexChanged.connect(combo_callback)
window.timer.timeout.connect(timer_callback)

window.show()
application.exec_()
