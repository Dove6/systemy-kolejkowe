from database import CachedAPI
from api import APIError
from gui import HiDpiApplication, MainWindow
from PyQt5.QtWidgets import QTableWidgetItem
from PyQt5.QtCore import Qt, QPointF, QDateTime


api = CachedAPI({
    'html': 'https://api.um.warszawa.pl/daneszcz.php?data=16c404ef084cfaffca59ef14b07dc516',
    'json': 'https://api.um.warszawa.pl/api/action/wsstore_get/'
}, 'cache.db')

application = HiDpiApplication([])
window = MainWindow()


def combo_callback(item_index):
    window.timer.stop()
    office_key = window.combo_box.itemData(item_index)
    try:
        matter_list = api.get_matter_list(office_key)
        window.chart.setSeriesCount(len(matter_list))
        window.table.setRowCount(len(matter_list))
        for index, matter in enumerate(matter_list):
            window.chart.series()[index].setData((matter['ordinal'], matter['group_id']))
            window.table.setItem(index, 0, QTableWidgetItem(str(index + 1)))
            window.table.item(index, 0).setForeground(window.chart.series()[index].color())
            window.table.item(index, 0).setTextAlignment(int(Qt.AlignRight | Qt.AlignVCenter))
            window.table.setItem(index, 1, QTableWidgetItem(matter['name']))
            window.table.item(index, 1).setTextAlignment(int(Qt.AlignLeft | Qt.AlignVCenter))
            sample_list = api.get_sample_list(office_key, matter['ordinal'], matter['group_id'])
            for sample in sample_list:
                window.chart.series()[index] << QPointF(
                    QDateTime.fromString(sample['time'], 'yyyy-MM-dd hh:mm').toMSecsSinceEpoch(),
                    sample['queue_length']
                )
                window.table.setItem(index, 2, QTableWidgetItem(str(sample['open_counters'])))
                window.table.item(index, 2).setTextAlignment(Qt.AlignCenter)
                window.table.setItem(index, 3, QTableWidgetItem(str(sample['queue_length'])))
                window.table.item(index, 3).setTextAlignment(Qt.AlignCenter)
                window.table.setItem(index, 4, QTableWidgetItem(sample['current_number']))
                window.table.item(index, 4).setTextAlignment(Qt.AlignCenter)
        window.timer.start()
    except APIError as e:
        print('[BŁĄD]')
        print(e)
        exit()


def timer_callback():
    office_key = window.combo_box.currentData()
    matter_key_list = map(lambda series: series.data(), window.chart.series())
    for index, matter_key in enumerate(matter_key_list):
        sample_list = api.get_sample_list(office_key, matter_key[0], matter_key[1])
        for sample in sample_list:
            window.chart.series()[index].movePoints(-1)
            window.chart.series()[index] << QPointF(
                QDateTime.fromString(sample['time'], 'yyyy-MM-dd hh:mm').toMSecsSinceEpoch(),
                sample['queue_length']
            )
            window.table.item(index, 2).setText(str(sample['open_counters']))
            window.table.item(index, 3).setText(str(sample['queue_length']))
            window.table.item(index, 4).setText(sample['current_number'])


office_list = sorted(api.get_office_list(), key=lambda x: x['name'])
window.combo_box.setItems([x['name'] for x in office_list], [x['key'] for x in office_list])
window.combo_box.currentIndexChanged.connect(combo_callback)
window.timer.timeout.connect(timer_callback)

window.show()
application.exec_()
