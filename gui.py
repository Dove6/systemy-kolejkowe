from PyQt5.QtWidgets import QApplication, QMainWindow, QComboBox, QLabel, QTableWidget, QVBoxLayout, QWidget, QAbstractItemView, QHeaderView
from PyQt5.QtCore import Qt, QPointF
from PyQt5.QtChart import QChart, QChartView, QLineSeries, QValueAxis
from database import SQLite3Cursor, get_matter_list


class HiDpiApplication(QApplication):
    def __init__(self, *args, **kwargs):
        # enable support for hi-dpi screens (https://leomoon.com/journal/python/high-dpi-scaling-in-pyqt5/)
        QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
        QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

        super().__init__(*args, **kwargs)


class ComboBox(QComboBox):
    def itemsTexts(self):
        texts = []
        for index in range(self.count()):
            texts.append(self.itemText(index))
        return texts

    def itemsData(self):
        data = []
        for index in range(self.count()):
            data.append(self.itemData(index))
        return data

    def setItems(self, texts, data=None):
        self.clear()
        self.addItems(texts)
        if data is not None:
            if len(texts) == len(data):
                for index in range(self.count()):
                    self.setItemData(index, data[index])


class LineChart(QChart):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        x_axis = QValueAxis()
        x_axis.setRange(0, 60)
        x_axis.setTickCount(7)
        self.addAxis(x_axis, Qt.AlignBottom)
        y_axis = QValueAxis()
        y_axis.setRange(0, 20)
        self.addAxis(y_axis, Qt.AlignLeft)

    def setSeriesCount(self, count):
        self.removeAllSeries()
        for i in range(count):
            series = LineSeries()
            self.addSeries(series)
            for axis in self.axes():
                series.attachAxis(axis)


class LineSeries(QLineSeries):
    def movePoints(self, x=0, y=0, truncate=False):
        if x != 0 or y != 0:
            points = self.pointsVector()
            for point in points:
                point.setX(point.x() + x)
                point.setY(point.y() + y)
            if truncate:
                if x < 0:
                    min_x = min([point.x() for point in points])
                    min_x -= x
                    points = filter(lambda point: point.x() >= min_x, points)
                elif x > 0:
                    max_x = max([point.x() for point in points])
                    max_x -= x
                    points = filter(lambda point: point.x() <= max_x, points)
                if y < 0:
                    min_y = min([point.y() for point in points])
                    min_y -= y
                    points = filter(lambda point: point.y() >= min_y, points)
                elif y > 0:
                    max_y = max([point.y() for point in points])
                    max_y -= y
                    points = filter(lambda point: point.y() <= max_y, points)
            self.replace(points)


class MainWindow(QMainWindow):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.resize(750, 550)

        self._combo_list = []
        self._chart_series = []

        self._combo = ComboBox()

        self._chart = LineChart()
        self._chart.setTitle('Tytuł')
        self._chart.legend().setVisible(False)
        self._chart_view = QChartView()
        self._chart_view.setChart(self._chart)

        self._table = QTableWidget(0, 5)
        self._table.setHorizontalHeaderLabels(['Lp.', 'Nazwa usługi', 'Liczba stanowisk', 'Długość kolejki', 'Aktualny numer'])
        self._table.verticalHeader().hide()
        self._table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self._table.setSelectionMode(QAbstractItemView.NoSelection)
        self._table.setShowGrid(False)
        self._table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self._table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self._table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self._table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self._table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeToContents)
        self._table.horizontalHeader().model().setHeaderData(1, Qt.Horizontal, Qt.AlignLeft, Qt.TextAlignmentRole)

        self._vbox_layout = QVBoxLayout()
        self._vbox_layout.addWidget(self._combo)
        self._vbox_layout.addWidget(self._chart_view)
        self._vbox_layout.addWidget(self._table)

        self._main_widget = QWidget()
        self._main_widget.setLayout(self._vbox_layout)
        self.setCentralWidget(self._main_widget)

        self._timer_id = None

    def startTimer(self, interval):
        if self._timer_id is None:
            self._timer_id = super().startTimer(interval)
        else:
            raise AssertionError('Timer already in use')

    def killTimer(self):
        if self._timer_id is not None:
            super().killTimer(self._timer_id)
            self._timer_id = None

    def timerEvent(self, event):
        print(event)
        if self._timer_id is not None and event.timerId() == self._timer_id:
            with SQLite3Cursor('cache.db') as cursor:
                matter_list = get_matter_list(cursor, self.combo_box.currentData())
            for index, group in enumerate(matter_list['result']['grupy']):
                self.chart.series()[index].movePoints(-1)
                self.chart.series()[index] << QPointF(60, group['liczbaKlwKolejce'])
                self.table.item(index, 0).setText(str(index + 1))
                self.table.item(index, 1).setText(group['nazwaGrupy'])
                self.table.item(index, 2).setText(str(group['liczbaCzynnychStan']))
                self.table.item(index, 3).setText(str(group['liczbaKlwKolejce']))
                self.table.item(index, 4).setText(group['aktualnyNumer'])
        else:
            super().timerEvent(event)

    def _update_chart(self):
        self._chart.removeAllSeries()
        for series in self._chart_series:
            line_series = QLineSeries()
            for point in series:
                line_series.append(*point)
            self._chart.addSeries(line_series)
        self._chart.createDefaultAxes()

    def close(self):
        self.killTimer()
        super().close()

    @property
    def combo_box(self):
        return self._combo

    @property
    def chart(self):
        return self._chart

    @property
    def table(self):
        return self._table


class Popup(QWidget):
    pass
