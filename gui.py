from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QComboBox, QTableWidget, QVBoxLayout, QWidget,
    QAbstractItemView, QHeaderView, QTableWidgetItem
)
from PyQt5.QtCore import Qt, QTimer, QDateTime, QPointF
from PyQt5.QtGui import QPainter, QColor, QFont
from PyQt5.QtChart import QChart, QChartView, QLineSeries, QValueAxis, QDateTimeAxis
from random import shuffle, randint


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
        self._top_series = None

    # last series = top series
    def setSeriesCount(self, count):
        self.removeAllSeries()
        colors = [QColor.fromHsl(
            360 * i // (count + 1),
            128,
            randint(96, 192)
        ) for i in range(count + 1)]
        shuffle(colors)
        for i in range(count + 1):
            series = LineSeries()
            series.setColor(colors[i])
            pen = series.pen()
            pen.setWidth(4)
            series.setPen(pen)
            self.addSeries(series)
            for axis in self.axes():
                series.attachAxis(axis)

    def topSeriesIndex(self):
        return self._top_series

    def setTopSeriesIndex(self, index):
        series = self.series()
        if index is None:
            self._top_series = index
            series[-1].replace([])
        elif index < len(self.series()) and index >= 0:
            self._top_series = index
            series[-1].replace(series[index].pointsVector())
            pen = series[index].pen()
            pen.setWidth(8)
            series[-1].setPen(pen)
        else:
            raise ValueError('Series index out of range')


class LineSeries(QLineSeries):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._user_data = None

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
        max_time = QDateTime.fromMSecsSinceEpoch(0)
        for sample in sample_list:
            time = QDateTime.fromString(sample['time'], 'yyyy-MM-dd hh:mm')
            point = PointF(
                time.toMSecsSinceEpoch(),
                sample['queue_length']
            )
            if type(self._user_data) is dict:
                name = self._user_data.get('name')
            else:
                name = None
            point.setUserData({
                'name': name,
                'open_counters': sample['open_counters'],
                'queue_length': sample['queue_length'],
                'current_number': sample['current_number']
            })
            points.append(point)
            if time > max_time:
                max_time = time
        self.replace(points)
        chart = self.chart()
        if chart is not None:
            if chart.topSeriesIndex() == chart.series().index(self):
                chart.series()[-1].replace(points)
        self.attachedAxes()[0].setRange(max_time.addSecs(-3600), max_time)
        self.attachedAxes()[0].hide()
        self.attachedAxes()[0].show()

    def userData(self):
        return self._user_data

    def setUserData(self, data):
        self._user_data = data


class PointF(QPointF):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._user_data = None

    def userData(self):
        return self._user_data

    def setUserData(self, data):
        self._user_data = data


class TableWidget(QTableWidget):
    def setRow(self, row, matter, color=Qt.black):
        self.setItem(row, 0, QTableWidgetItem(str(row + 1)))
        self.setItem(row, 1, QTableWidgetItem(matter['name']))
        self.setItem(row, 2, QTableWidgetItem())
        self.setItem(row, 3, QTableWidgetItem())
        self.setItem(row, 4, QTableWidgetItem())
        self.item(row, 0).setBackground(color)
        self.item(row, 0).setForeground(Qt.white)
        font = self.item(row, 0).font()
        font.setWeight(QFont.Bold)
        self.item(row, 0).setFont(font)
        self.item(row, 0).setTextAlignment(int(Qt.AlignRight | Qt.AlignVCenter))
        self.item(row, 1).setTextAlignment(int(Qt.AlignLeft | Qt.AlignVCenter))

    def updateRow(self, row, sample_list):
        if len(sample_list) > 0:
            latest_sample = max(
                sample_list,
                key=lambda sample: QDateTime.fromString(sample['time'], 'yyyy-MM-dd hh:mm')
            )
            self.item(row, 2).setText(str(latest_sample['open_counters']))
            self.item(row, 3).setText(str(latest_sample['queue_length']))
            self.item(row, 4).setText(latest_sample['current_number'])

    def selectionChanged(self, selected, deselected):
        super().selectionChanged(selected, deselected)
        selected_indexes = selected.indexes()
        if len(selected_indexes) > 0:
            index = selected_indexes[0].row()
        else:
            index = None
        self.window()._chart.setTopSeriesIndex(index)


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
        self._table.horizontalHeader().setHighlightSections(False)
        self._table.verticalHeader().hide()
        self._table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self._table.setSelectionMode(QAbstractItemView.SingleSelection)
        self._table.setSelectionBehavior(QAbstractItemView.SelectRows)
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
