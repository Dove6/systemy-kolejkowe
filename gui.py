from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QComboBox, QTableWidget, QVBoxLayout, QWidget,
    QAbstractItemView, QHeaderView, QTableWidgetItem
)
from PyQt5.QtCore import Qt, QTimer, QDateTime, QPointF, QItemSelection, QThread, pyqtSignal
from PyQt5.QtGui import QPainter, QColor, QFont
from PyQt5.QtChart import QChart, QChartView, QLineSeries, QValueAxis, QDateTimeAxis
from random import shuffle, randint

from typing import Union, Optional, Dict, List, Tuple, Any
from retrying import retry

from database import MatterData, SampleList, CachedAPI


class HiDpiApplication(QApplication):
    '''
    QApplication's subclass supporting hi-dpi scaling by default.

    Qt method naming convention is preserved.

    :param `*args`: Positional arguments passed to QApplication constructor
    :param `**kwargs`: Named arguments passed to QApplication constructor
    '''
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        # Enable support for hi-dpi screens
        # https://leomoon.com/journal/python/high-dpi-scaling-in-pyqt5/
        QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
        QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

        super().__init__(*args, **kwargs)


class ComboBox(QComboBox):
    '''
    Subclass of QComboBox adding some useful methods to the original.

    Qt method naming convention is preserved.

    For documentation of constructor parameters, check QComboBox description:
    the constructor isn't overriden.
    '''
    def itemsTexts(self) -> List[str]:
        '''
        Get list of text content of combo box's items.

        :returns: List of texts representing each combo box item
        '''
        texts = []
        for index in range(self.count()):
            texts.append(self.itemText(index))
        return texts

    def itemsData(self) -> List[Any]:
        '''
        Get list of user data of combo box's items.

        :returns: List of user data stored in each combo box item
        '''
        data = []
        for index in range(self.count()):
            data.append(self.itemData(index))
        return data

    def setItems(
            self, texts: List[str], data: Optional[List[Any]] = None) -> None:
        '''
        Replace current combo box content with provided items.
        If provided, append user data to them.

        :param texts: List of texts representing new combo box items
        :param data: List of user data to be associated with new combo box
            items
        '''
        self.clear()
        self.addItems(texts)
        if data is not None:
            if len(texts) != len(data):
                raise AssertionError(
                    'Lists of texts and associated data must be of the same'
                    'length')
            for index in range(self.count()):
                self.setItemData(index, data[index])


class QueueSystemChart(QChart):
    '''
    Subclass of QChart for displaying and managing time samples data
    associated with queue systems of Warsaw.

    Qt method naming convention is preserved.

    :param `*args`: Positional arguments passed to QChart constructor
    :param `**kwargs`: Named arguments passed to QChart constructor
    :ivar _top_series: Index of series portrayed as topmost series in graph
        (covering other series).
        Getter: topSeriesIndex.
        Setter: setTopSeriesIndex.
    '''
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        # Setup horizontal axis
        x_axis = QDateTimeAxis()
        x_axis.setFormat('hh:mm')
        x_axis.setTickCount(7)
        current_time = QDateTime.currentDateTime()
        x_axis.setRange(current_time.addSecs(-3600), current_time)
        x_axis.setTitleText('Godzina [hh:mm]')
        self.addAxis(x_axis, Qt.AlignBottom)
        # Setup vertical axis
        y_axis = QValueAxis()
        y_axis.setRange(0, 20)
        y_axis.setTitleText('Liczba osób w kolejce')
        self.addAxis(y_axis, Qt.AlignLeft)

        self.legend().setVisible(False)
        self._top_series: Optional[int] = None

    def setSeriesCount(self, count: int) -> None:
        '''
        Clear the chart and add specified count of series to it.

        Actually, the chart will have one more series than specified:
        the topmost one simulating bringing chosen series to top.

        :param count: Count of series to set.
        '''
        self.removeAllSeries()
        for i in range(count + 1):
            series = QueueSystemSeries()
            pen = series.pen()
            pen.setWidth(4)
            series.setPen(pen)
            self.addSeries(series)
            for axis in self.axes():
                series.attachAxis(axis)

    def setSeriesSamples(
            self, series_index: int, sample_list: SampleList) -> None:
        '''
        Set sample data of specified series.

        :param series_index: Index of series which data is to be set
        :param sample_list: List of time samples
        '''
        if 0 <= series_index < len(self.series()):
            self.series()[series_index].setSamples(sample_list)

    def setSeriesData(
            self, series_index: int, user_data: Any, color: QColor) -> None:
        '''
        Set user and color data of specified series.

        :param series_index: Index of series which data is to be set
        :param user_data: User data
        :param color: Color of series
        '''
        if 0 <= series_index < len(self.series()):
            self.series()[series_index].setUserData(user_data)
            self.series()[series_index].setColor(color)

    def topSeriesIndex(self) -> Optional[int]:
        '''
            Get index of topmost series (if any is set).

            :returns: Index of series portrayed as topmost (may be None)
        '''
        return self._top_series

    def setTopSeriesIndex(self, index: Optional[int]) -> None:
        '''
            Set index of topmost series.

            :param index: Index of series to be portrayed as topmost or None
                (for resetting state of actual topmost series)
        '''
        series = self.series()
        if index is None:
            # If index is None, reset the actual topmost series data
            self._top_series = index
            series[-1].replace([])
        elif index < len(self.series()) and index >= 0:
            # If index exists, style the actual topmost series to resemble
            # the one portrayed as topmost
            self._top_series = index
            series[-1].replace(series[index].pointsVector())
            pen = series[index].pen()
            pen.setWidth(8)
            series[-1].setPen(pen)
        else:
            raise ValueError('Series index out of range')


class QueueSystemSeries(QLineSeries):
    '''
    Subclass of QLineSeries for encapsulating time samples data associated
    with queue systems of Warsaw.

    Qt method naming convention is preserved.

    :param parent: Parent widget (optional) passed to QLineSeries constructor
    :ivar _user_data: Arbitrary user data.
        Getter: userData.
        Setter: setUserData.
    '''
    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._user_data: Any = None

    def setSamples(self, sample_list: SampleList) -> None:
        '''
        Replace current point data with given time samples.

        :param sample_list: Queue time samples to replace series data with
        '''
        points = []
        max_time = QDateTime.fromMSecsSinceEpoch(0)
        max_value = 10
        # Parse sample data
        for sample in sample_list:
            time = QDateTime.fromString(sample['time'], 'yyyy-MM-dd hh:mm')
            point = DetailedPointF(
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
            # Look for the newest sample time...
            if time > max_time:
                max_time = time
            # ...and the greates sample value
            if sample['queue_length'] > max_value:
                max_value = sample['queue_length']
        self.replace(points)
        chart = self.chart()
        if chart is not None:
            if chart.topSeriesIndex() == chart.series().index(self):
                chart.series()[-1].replace(points)
        # Move chart's horizontal axis according to the newest sample
        self.attachedAxes()[0].setRange(max_time.addSecs(-3600), max_time)
        self.attachedAxes()[0].hide()
        self.attachedAxes()[0].show()
        # Scale chart's vertical axis according to the greatest sample
        self.attachedAxes()[1].setMax(max_value)
        self.attachedAxes()[1].hide()
        self.attachedAxes()[1].show()

    def userData(self) -> Any:
        '''
        Get user data associated with the series.

        :returns: Arbitrary user data assigned to the series
        '''
        return self._user_data

    def setUserData(self, data: Any):
        '''
        Associate user data with the series.

        :param data: Arbitrary user data to be assigned to the series
        '''
        self._user_data = data


class DetailedPointF(QPointF):
    '''
    Subclass of QPointF with an additional property: user data.

    Qt method naming convention is preserved.

    :param `*args`: Positional arguments passed to QPointF constructor
    :param `**kwargs`: Named arguments passed to QPointF constructor
    :ivar _user_data: Arbitrary user data.
        Getter: userData.
        Setter: setUserData.
    '''
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._user_data: Any = None

    def userData(self) -> Any:
        '''
        Get user data associated with the point.

        :returns: Arbitrary user data assigned to the point
        '''
        return self._user_data

    def setUserData(self, data: Any):
        '''
        Associate user data with the point.

        :param data: Arbitrary user data to be assigned to the point
        '''
        self._user_data = data


class QueueSystemTable(QTableWidget):
    '''
    Subclass of QTableWidget for displaying (only) current time samples data
    associated with queue systems of Warsaw.

    Qt method naming convention is preserved.

    :param parent: Parent widget (optional) passed to QTableWidget constructor
    :ivar _top_series: Index of series portrayed as topmost series in graph
        (covering other series).
        Getter: topSeriesIndex.
        Setter: setTopSeriesIndex.
    '''
    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(0, 5, parent)
        # Setup and style the horizontal header
        self.setHorizontalHeaderLabels([
            'Lp.',
            'Nazwa usługi',
            'Liczba stanowisk',
            'Długość kolejki',
            'Aktualny numer'
        ])
        self.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeToContents)
        self.horizontalHeader().model().setHeaderData(
            1,
            Qt.Horizontal,
            Qt.AlignLeft | Qt.AlignVCenter,
            Qt.TextAlignmentRole
        )
        self.horizontalHeader().setHighlightSections(False)
        # Get rid of the vertical header...
        self.verticalHeader().hide()
        # ...and the possibility of editing cells by the user
        self.setEditTriggers(QAbstractItemView.NoEditTriggers)
        # Setup selection characteristics
        self.setSelectionMode(QAbstractItemView.SingleSelection)
        self.setSelectionBehavior(QAbstractItemView.SelectRows)
        # Hide grid
        self.setShowGrid(False)

    def setRow(self, row: int, matter: MatterData, color: QColor = Qt.black) -> None:
        '''
        Initialize an empty table row.

        :param row: Row's index
        :param matter: Data of administrative matter associated with the row
        :param color: Color of chart series associated with the row
        '''
        self.setItem(row, 0, QTableWidgetItem(str(row + 1)))
        self.setItem(row, 1, QTableWidgetItem(matter['name']))
        self.setItem(row, 2, QTableWidgetItem())
        self.setItem(row, 3, QTableWidgetItem())
        self.setItem(row, 4, QTableWidgetItem())
        # Set first cell's background to the color of corresponding chart
        # series
        self.item(row, 0).setBackground(color)
        self.item(row, 0).setForeground(Qt.white)
        font = self.item(row, 0).font()
        font.setWeight(QFont.Bold)
        self.item(row, 0).setFont(font)
        self.item(row, 0).setTextAlignment(int(Qt.AlignRight | Qt.AlignVCenter))
        self.item(row, 1).setTextAlignment(int(Qt.AlignLeft | Qt.AlignVCenter))

    def updateRow(self, row: int, sample_list: SampleList) -> None:
        '''
        Update row's data.

        :param row: Row's index
        :param sample_list: List of time samples for administrative matter
            associated with the row
        '''
        if len(sample_list) > 0:
            # Table shows only the newest sample
            latest_sample = max(
                sample_list,
                key=lambda sample: QDateTime.fromString(sample['time'], 'yyyy-MM-dd hh:mm')
            )
            self.item(row, 2).setText(str(latest_sample['open_counters']))
            self.item(row, 3).setText(str(latest_sample['queue_length']))
            self.item(row, 4).setText(latest_sample['current_number'])

    def selectionChanged(self, selected: QItemSelection, deselected: QItemSelection) -> None:
        '''
        Process event of change of selection: set selected matter as a topmost
        chart series.
        (overriden internal function)

        :param selected: Newly-selected items
        :param selected: Just-deselected items
        '''
        super().selectionChanged(selected, deselected)
        selected_indexes = selected.indexes()
        if len(selected_indexes) > 0:
            # If a row was selected, get its index
            index = selected_indexes[0].row()
        else:
            index = None
        self.window()._chart.setTopSeriesIndex(index)


class CacheThread(QThread):
    '''
    Subclass of QThread used for asynchronously updating the cache data.

    Qt method and signal naming convention is preserved.

    :param api: CachedAPI object to update
    :cvar succeeded: pyqtSignal emitted on successful thread execution
    :cvar failed: pyqtSignal emitted on any exception
    :ivar _api: CachedAPI provided in constructor
    '''
    succeeded: pyqtSignal = pyqtSignal()
    failed: pyqtSignal = pyqtSignal(Exception)

    def __init__(self, api: CachedAPI) -> None:
        super().__init__()
        self._api: CachedAPI = api

    def run(self) -> None:
        try:
            self._api.update()
            self.succeeded.emit()
        except Exception as e:
            self.failed.emit(e)


class GUISetupThread(QThread):
    '''
    Subclass of QThread used for asynchronously setting up GUI elements for
    future updates.

    Qt method and signal naming convention is preserved.

    :param api: CachedAPI used for fetching data
    :cvar got_matter_count: signal emitted after getting matter count
    :cvar got_matter: signal emitted after fetching a single matter data
    :cvar succeeded: pyqtSignal emitted on successful thread execution
    :cvar failed: pyqtSignal emitted on any exception
    :ivar _api: CachedAPI provided in constructor
    '''
    gotMatter = pyqtSignal(int, dict, QColor)
    gotMatterCount = pyqtSignal(int)
    succeeded: pyqtSignal = pyqtSignal()
    failed: pyqtSignal = pyqtSignal(Exception)

    def __init__(self, api: CachedAPI) -> None:
        super().__init__()
        self._api: CachedAPI = api

    def run(self) -> None:
        matter_list = self._api.get_matter_list()
        self.gotMatterCount.emit(len(matter_list))
        # Generate distinct colors associated with matters
        colors = [QColor.fromHsl(
            360 * i // (len(matter_list) + 1),
            128,
            randint(96, 192)
        ) for i in range(len(matter_list) + 1)]
        shuffle(colors)
        for index, matter in enumerate(matter_list):
            self.gotMatter.emit(index, matter, colors[index])


class GUIUpdateThread(QThread):
    '''
    Subclass of QThread used for asynchronously updating the data displayed
    by GUI.

    Qt method and signal naming convention is preserved.

    :param api: CachedAPI used for fetching data
    :param chart: QueueSystemChart with series containing identifiers
        of administrative matters (set as user data)
    :cvar got_sample_list: signal emitted after fetching sample list
    :cvar succeeded: pyqtSignal emitted on successful thread execution
    :cvar failed: pyqtSignal emitted on any exception
    :ivar _api: CachedAPI provided in constructor
    :ivar _chart: Chart provided in constructor
    '''
    gotSampleList = pyqtSignal(int, list)
    succeeded: pyqtSignal = pyqtSignal()
    failed: pyqtSignal = pyqtSignal(Exception)

    def __init__(self, api: CachedAPI, chart: QueueSystemChart) -> None:
        super().__init__()
        self._api: CachedAPI = api
        self._chart: QueueSystemChart = chart

    def run(self) -> None:
        try:
            matter_key_list = map(
                lambda series: series.userData(), self._chart.series())
            for index, matter_key in enumerate(matter_key_list):
                if matter_key is not None:
                    sample_list = self._api.get_sample_list(
                        matter_key['ordinal'], matter_key['group_id'])
                    self.gotSampleList.emit(index, sample_list)
            self.succeeded.emit()
        except Exception as e:
            self.failed.emit(e)


class QueueSystemWindow(QMainWindow):
    '''
    Subclass of QMainWindow, center of the whole application, setting up
    widgets and connecting signals to callbacks.

    Qt method naming convention is preserved.

    :param api: CachedAPI object used for fetching queue system data
    :param `*args`: Positional arguments passed to QMainWindow constructor
    :param `**kwargs`: Named arguments passed to QMainWindow constructor
    :ivar _api: CachedAPI provided in constructor
    :ivar _combo: Window's combo box object
    :ivar _chart: Window's chart of queue data samples object
    :ivar _table: Window's table of administrative matters object
    :ivar _timer: Window's API call timer
    :ivar _threads: Window's dictionary of threads used for updating API
        and GUI data
    '''
    def __init__(self, api: CachedAPI, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._api: CachedAPI = api
        # Set window's size
        self.resize(750, 550)
        # Create ComboBox object
        self._combo: ComboBox = ComboBox()
        # Create and setup chart and its view
        self._chart: QueueSystemChart = QueueSystemChart()
        chart_view = QChartView()
        chart_view.setChart(self._chart)
        chart_view.setRenderHint(QPainter.Antialiasing)
        # Create the table
        self._table: QueueSystemTable = QueueSystemTable()
        # Create window's layout and place elements in it
        vbox_layout = QVBoxLayout()
        vbox_layout.addWidget(self._combo)
        vbox_layout.addWidget(chart_view)
        vbox_layout.addWidget(self._table)
        # Create central window's widget and apply layout to it
        main_widget = QWidget()
        main_widget.setLayout(vbox_layout)
        self.setCentralWidget(main_widget)
        # Create the timer
        self._timer: QTimer = QTimer()
        self._timer.setInterval(api.cooldown)
        # Create the dictionary of threads
        self._threads: Dict[str, QThread] = {
            'caching': CacheThread(api),
            'displaying': GUIUpdateThread(api, self._chart),
            'setting': GUISetupThread(api)
        }
        # Connect all threads' failed signals to exception logging function
        for thread in self._threads.values():
            thread.failed.connect(self._print_exception)
        # Connect caching thread's succeeded signal to a method starting GUI
        # update
        self._threads['caching'].succeeded.connect(
            self._threads['displaying'].start)
        # Connect GUI updating thread's got_sample_list signal to methods
        # updating table values and chart series' values
        self._threads['displaying'].gotSampleList.connect(
            self._table.updateRow)
        self._threads['displaying'].gotSampleList.connect(
            self._chart.setSeriesSamples)
        # Connect GUI setting thread's got_matter_count signal to methods
        # changing number of table rows ang chart series
        self._threads['setting'].gotMatterCount.connect(
            self._table.setRowCount)
        self._threads['setting'].gotMatterCount.connect(
            self._chart.setSeriesCount)
        # Connect GUI setting thread's got_matter signal to methods changing
        # table rows' descriptions and chart series' data
        self._threads['setting'].gotMatter.connect(
            self._table.setRow)
        self._threads['setting'].gotMatter.connect(
            self._chart.setSeriesData)
        # Connect GUI setting thread's finished signal to a callback
        # responsible for preparing just-set widgets for updates
        self._threads['setting'].finished.connect(
            self._prepare_widgets_for_updates)
        # Connect (cyclical) timer's timeout signal to a method starting cache
        # update
        self._timer.timeout.connect(self._threads['caching'].start)

        # Get list of available offices and display it in combo box
        office_list = sorted(api.get_office_list(), key=lambda x: x['name'])
        self._combo.setItems(
            [x['name'] for x in office_list], [x['key'] for x in office_list])
        # Insert placeholder value
        self._combo.insertItem(0, 'Wybierz urząd...', 'placeholder')
        self._combo.setCurrentIndex(0)
        # Connect combo box's index changing signal to appropriate callback
        # (responsible for resetting table names and reconnecting series with
        # them)
        self._combo.currentIndexChanged.connect(self._setup_widgets_content)

    def _setup_widgets_content(self, item_index: int) -> None:
        '''
        Setup widgets settings and content according to office chosen from
        the list.
        (callback function)

        :param item_index: Item of combo box's item chosen by the user
        '''
        # Stop timer to stop updates of widgets
        self._timer.stop()
        # If placeholder exists, remove it
        if self._combo.itemData(0) == 'placeholder':
            # Disconnect currentIndexChanged signal not to trigger it during
            # removement
            self._combo.currentIndexChanged.disconnect()
            self._combo.removeItem(0)
            item_index -= 1
            # Reconnect the signal
            self._combo.currentIndexChanged.connect(self._setup_widgets_content)
        # Prevent caching thread from triggering the GUI updating thread
        try:
            self._threads['caching'].succeeded.disconnect()
        except TypeError:
            # If nothin is connected to the signal, an exception will be
            # raised
            pass
        # Make GUI setup thread run after caching data
        self._threads['caching'].finished.connect(
            self._threads['setting'].start)
        # Change the office_key parameter of API object to the identifier
        # of newly chosen office
        self._api.office_key = self._combo.itemData(item_index)
        # Refresh database data and setup the widgets after it
        self._threads['caching'].start()

    def _prepare_widgets_for_updates(self) -> None:
        # Remove the connection to this callback
        try:
            self._threads['caching'].finished.disconnect()
        except TypeError:
            # If nothin is connected to the signal, an exception will be
            # raised
            pass
        # Reconnect succeeded signal to the GUI update thread
        self._threads['caching'].succeeded.connect(
            self._threads['displaying'].start)
        # Cache and display queue system data
        self._threads['caching'].start()
        # Start timer again in order to update the widgets cyclically
        self._timer.start()

    def _print_exception(self, exception: Exception) -> None:
        print('Exception occured in GUI subthreads:')
        print(exception)

    def close(self) -> None:
        '''
        Close the window and clean up.
        (internal function)
        '''
        # Stop the timer
        self._timer.stop()
        # Exit the threads
        for thread in self._threads.values():
            thread.quit()
        super().close()

    @property
    def combo_box(self) -> ComboBox:
        '''
        Window's combo box
        '''
        return self._combo

    @property
    def chart(self) -> QueueSystemChart:
        '''
        Window's chart
        '''
        return self._chart

    @property
    def table(self) -> QueueSystemTable:
        '''
        Window's table
        '''
        return self._table

    @property
    def timer(self) -> QTimer:
        '''
        Window's timer
        '''
        return self._timer
