from PyQt5.QtWidgets import QApplication, QMainWindow, QComboBox, QLabel, QTableView
from PyQt5.QtCore import Qt
from PyQt5.QtCharts import QChartView

# Enable support for hi-dpi screens (https://leomoon.com/journal/python/high-dpi-scaling-in-pyqt5/)
QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

application = QApplication([])


