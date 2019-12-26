from PyQt5.QtWidgets import QApplication, QMainWindow, QComboBox, QLabel, QTableView, QVBoxLayout, QWidget
from PyQt5.QtCore import Qt
from PyQt5.QtChart import QChart, QChartView, QBarSet, QBarCategoryAxis, QLineSeries


class MainWindow(QMainWindow):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        vbox_layout = QVBoxLayout()
        combo = QComboBox()
        vbox_layout.addWidget(combo)
        chart = QChartView()
        vbox_layout.addWidget(chart)
        table = QTableView()
        vbox_layout.addWidget(table)
        main_widget = QWidget()
        main_widget.setLayout(vbox_layout)
        self.setCentralWidget(main_widget)

class Popup(QWidget):
    pass


# Enable support for hi-dpi screens (https://leomoon.com/journal/python/high-dpi-scaling-in-pyqt5/)
QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

application = QApplication([])

window = MainWindow()
window.show()
application.exec_()
