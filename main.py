from database import CachedAPI
from api import APIError
from gui import HiDpiApplication, MainWindow

api_urls = {
    'html': 'https://api.um.warszawa.pl/daneszcz.php?data=16c404ef084cfaffca59ef14b07dc516',
    'json': 'https://api.um.warszawa.pl/api/action/wsstore_get/'
}

api = CachedAPI(api_urls['html'], api_urls['json'], 'cache.db')

application = HiDpiApplication([])
window = MainWindow(api)

if __name__ == '__main__':
    window.show()
    application.exec_()
