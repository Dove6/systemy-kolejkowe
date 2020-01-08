from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QComboBox, QTableWidget, QVBoxLayout, QWidget,
    QAbstractItemView, QHeaderView, QTableWidgetItem
)
from PyQt5.QtCore import Qt, QTimer, QDateTime, QPointF
from PyQt5.QtGui import QPainter
from PyQt5.QtChart import QChart, QChartView, QLineSeries, QValueAxis, QDateTimeAxis


class HiDpiApplication(QApplication):
    def __init__(self, *args, **kwargs):
        # enable support for hi-dpi screens
        # https://leomoon.com/journal/python/high-dpi-scaling-in-pyqt5/
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
        x_axis = QDateTimeAxis()
        x_axis.setFormat('hh:mm')
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
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._data = {}

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

    def setSamples(self, sample_list):
        points = []
        max_time = self.attachedAxes()[0].max()
        for sample in sample_list:
            time = QDateTime.fromString(sample['time'], 'yyyy-MM-dd hh:mm')
            point = PointF(
                time.toMSecsSinceEpoch(),
                sample['queue_length']
            )
            point.setUserData({
                'open_counters': sample['open_counters'],
                'queue_length': sample['queue_length'],
                'current_number': sample['current_number']
            })
            points.append(point)
            if time > max_time:
                max_time = time
        self.replace(points)
        self.attachedAxes()[0].setRange(max_time.addSecs(-3600), max_time)
        self.attachedAxes()[0].hide()
        self.attachedAxes()[0].show()
        # window.table.item(index, 2).setText(str(sample['open_counters']))
        # window.table.item(index, 3).setText(str(sample['queue_length']))
        # window.table.item(index, 4).setText(sample['current_number'])

    def userData(self):
        return self._user_data

    def setUserData(self, data):
        self._user_data = data


class PointF(QPointF):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._user_data = None

    def userData(self):
        return self._userData

    def setUserData(self, data):
        self._userData = data


class TableWidget(QTableWidget):
    def setRow(self, row, matter, color=Qt.black):
        self.setItem(row, 0, QTableWidgetItem(str(row + 1)))
        self.setItem(row, 1, QTableWidgetItem(matter['name']))
        self.setItem(row, 2, QTableWidgetItem())
        self.setItem(row, 3, QTableWidgetItem())
        self.setItem(row, 4, QTableWidgetItem())
        self.item(row, 0).setForeground(color)
        self.item(row, 0).setTextAlignment(int(Qt.AlignRight | Qt.AlignVCenter))
        self.item(row, 1).setTextAlignment(int(Qt.AlignLeft | Qt.AlignVCenter))

    def updateRow(self, row, sample_list):
        latest_sample = max(
            sample_list,
            key=lambda sample: QDateTime.fromString(sample['time'], 'yyyy-MM-dd hh:mm')
        )
        self.item(row, 2).setText(str(latest_sample['open_counters']))
        self.item(row, 3).setText(str(latest_sample['queue_length']))
        self.item(row, 4).setText(latest_sample['current_number'])


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
        self._chart_view.setRenderHint(QPainter.Antialiasing)

        self._table = TableWidget(0, 5)
        self._table.setHorizontalHeaderLabels([
            'Lp.',
            'Nazwa usługi',
            'Liczba stanowisk',
            'Długość kolejki',
            'Aktualny numer'
        ])
        self._table.verticalHeader().hide()
        self._table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self._table.setSelectionMode(QAbstractItemView.NoSelection)
        self._table.setShowGrid(False)
        self._table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self._table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self._table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self._table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self._table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeToContents)
        self._table.horizontalHeader().model().setHeaderData(
            1,
            Qt.Horizontal,
            Qt.AlignLeft | Qt.AlignVCenter,
            Qt.TextAlignmentRole
        )

        self._vbox_layout = QVBoxLayout()
        self._vbox_layout.addWidget(self._combo)
        self._vbox_layout.addWidget(self._chart_view)
        self._vbox_layout.addWidget(self._table)

        self._main_widget = QWidget()
        self._main_widget.setLayout(self._vbox_layout)
        self.setCentralWidget(self._main_widget)

        self._timer = QTimer()
        print('Warning: too short API polling interval')
        self._timer.setInterval(5000)

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

    @property
    def timer(self):
        return self._timer


class Popup(QWidget):
    pass
