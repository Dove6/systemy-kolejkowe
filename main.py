'''
Main file executing the application.
'''
from database import CachedAPI
from gui import HiDpiApplication, QueueSystemWindow

# URLs used for connecting to the API
# html: HTML-based reply
# json: JSON reply
api_urls = {
    'html': 'https://api.um.warszawa.pl/daneszcz.php?data=16c404ef084cfaffca59ef14b07dc516',
    'json': 'https://api.um.warszawa.pl/api/action/wsstore_get/'
}

# Create cached API object
api = CachedAPI(api_urls['html'], api_urls['json'], 'cache.db')
# and set minimum time between API requests (in seconds)
api.cooldown = 60

# Initialize GUI
application = HiDpiApplication([])
window = QueueSystemWindow(api)

if __name__ == '__main__':
    # Run the application
    window.show()
    application.exec_()
