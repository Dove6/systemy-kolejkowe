from PyQt5.QtWidgets import QApplication, QMainWindow, QComboBox, QLabel, QTableWidget, QVBoxLayout, QWidget
from PyQt5.QtCore import Qt
from PyQt5.QtChart import QChart, QChartView, QLineSeries


class MainWindow(QMainWindow):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.resize(750, 550)

        self._combo_list = []
        self._chart_series = []

        self._combo = QComboBox()

        self._chart = QChart()
        self._chart.setTitle('Tytuł')
        self._chart.legend().setVisible(False)
        self._chart_view = QChartView()
        self._chart_view.setChart(self._chart)

        self._table = QTableWidget()

        self._vbox_layout = QVBoxLayout()
        self._vbox_layout.addWidget(self._combo)
        self._vbox_layout.addWidget(self._chart_view)
        self._vbox_layout.addWidget(self._table)

        self._main_widget = QWidget()
        self._main_widget.setLayout(self._vbox_layout)
        self.setCentralWidget(self._main_widget)

    def _update_chart(self):
        self._chart.removeAllSeries()
        for series in self._chart_series:
            line_series = QLineSeries()
            for point in series:
                line_series.append(*point)
            self._chart.addSeries(line_series)
        self._chart.createDefaultAxes()

    @property
    def chart_series(self):
        return self._chart_series[:]

    @chart_series.setter
    def chart_series(self, value):
        self._chart_series = value[:]
        self._update_chart()

    def _update_combo(self):
        self._combo.clear()
        self._combo.addItems(self._combo_list)

    @property
    def combo_list(self):
        return self._combo_list[:]

    @combo_list.setter
    def combo_list(self, value):
        self._combo_list = value[:]
        self._update_combo()


class Popup(QWidget):
    pass


# Enable support for hi-dpi screens (https://leomoon.com/journal/python/high-dpi-scaling-in-pyqt5/)
QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

application = QApplication([])

window = MainWindow()
window.show()
application.exec_()
