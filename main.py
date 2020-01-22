from database import CachedAPI
from api import APIError
from gui import HiDpiApplication, MainWindow
from threading import Thread


api_urls = {
    'html': 'https://api.um.warszawa.pl/daneszcz.php?data=16c404ef084cfaffca59ef14b07dc516',
    'json': 'https://api.um.warszawa.pl/api/action/wsstore_get/'
}

api = CachedAPI(api_urls['html'], api_urls['json'], 'cache.db')

application = HiDpiApplication([])
window = MainWindow()


def combo_callback(item_index):
    if window.combo_box.itemData(0) == 'placeholder':
        window.combo_box.currentIndexChanged.disconnect(combo_callback)
        window.combo_box.removeItem(0)
        item_index -= 1
        window.combo_box.currentIndexChanged.connect(combo_callback)
    window.timer.stop()
    api.office_key = window.combo_box.itemData(item_index)
    try:
        Thread(target=api.update).start()
        matter_list = api.get_matter_list()
        window.chart.setSeriesCount(len(matter_list))
        window.table.setRowCount(len(matter_list))
        for index, matter in enumerate(matter_list):
            window.chart.series()[index].setUserData({
                'name': matter['name'],
                'ordinal': matter['ordinal'],
                'group_id': matter['group_id']
            })
            window.table.setRow(index, matter, window.chart.series()[index].color())
            sample_list = api.get_sample_list(matter['ordinal'], matter['group_id'])
            window.chart.series()[index].setSamples(sample_list)
            window.table.updateRow(index, sample_list)
        window.timer.start()
    except APIError as e:
        print('[BŁĄD]')
        print(e)
        exit()


def timer_callback():
    try:
        Thread(target=api.update).start()
        matter_key_list = map(lambda series: series.userData(), window.chart.series())
        for index, matter_key in enumerate(matter_key_list):
            if matter_key is not None:
                sample_list = api.get_sample_list(matter_key['ordinal'], matter_key['group_id'])
                window.chart.series()[index].setSamples(sample_list)
                window.table.updateRow(index, sample_list)
    except APIError as e:
        print('[BŁĄD]')
        print(e)
        exit()


office_list = sorted(api.get_office_list(), key=lambda x: x['name'])
window.combo_box.setItems([x['name'] for x in office_list], [x['key'] for x in office_list])
window.combo_box.insertItem(0, 'Wybierz urząd...', 'placeholder')
window.combo_box.setCurrentIndex(0)
window.combo_box.currentIndexChanged.connect(combo_callback)
window.timer.timeout.connect(timer_callback)

if __name__ == '__main__':
    window.show()
    application.exec_()
