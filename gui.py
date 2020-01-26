from functools import partial
from random import shuffle, randint
from typing import Union, Optional, Dict, List, Any

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QComboBox, QTableWidget, QVBoxLayout, QWidget,
    QAbstractItemView, QHeaderView, QTableWidgetItem, QStatusBar, QLabel, QCheckBox
)
from PyQt5.QtCore import Qt, QTimer, QDateTime, QPointF, QItemSelection, QThread, pyqtSignal, QSize, QSettings
from PyQt5.QtGui import QPainter, QColor, QFont, QIcon, QMovie, QResizeEvent, QMoveEvent
from PyQt5.QtChart import QChart, QChartView, QLineSeries, QValueAxis, QDateTimeAxis

from api import APIError
from database import MatterData, SampleList, CachedAPI, DatabaseError


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
        x_axis.setTitleText('Godzina [hh:mm]')
        self.addAxis(x_axis, Qt.AlignBottom)
        # Setup vertical axis
        y_axis = QValueAxis()
        y_axis.setTitleText('Liczba osób w kolejce')
        self.addAxis(y_axis, Qt.AlignLeft)
        self.resetAxes()

        self.legend().setVisible(False)
        self._top_series: Optional[int] = None

    def resetAxes(self) -> None:
        '''
        Reset chart's axes to default ranges
        '''
        x_axis, y_axis = self.axes()
        current_time = QDateTime.currentDateTime()
        x_axis.setRange(current_time.addSecs(-3600), current_time)
        x_axis.hide()
        x_axis.show()
        y_axis.setMax(10)
        y_axis.hide()
        y_axis.show()

    def setSeriesCount(self, count: int) -> None:
        '''
        Clear the chart and add specified count of series to it.

        Actually, the chart will have one more series than specified:
        the topmost one simulating bringing chosen series to top.

        :param count: Count of series to set.
        '''
        self.removeAllSeries()
        for _ in range(count + 1):
            series = QueueSystemSeries()
            pen = series.pen()
            pen.setWidth(4)
            series.setPen(pen)
            self.addSeries(series)
            for axis in self.axes():
                series.attachAxis(axis)
        self.resetAxes()

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
        elif 0 <= index < len(self.series()):
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
            if isinstance(self._user_data, dict):
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

    def setUserData(self, data: Any) -> None:
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

    def setUserData(self, data: Any) -> None:
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
        self.window().chart.setTopSeriesIndex(index)


class Settings(QSettings):
    def __init__(self, filename: str = 'settings.ini') -> None:
        super().__init__(filename, QSettings.IniFormat)

    def value(
            self, key: str, default_value: Any = None,
            value_type: type = type(None),
            set_if_missing: bool = False) -> None:
        if isinstance(None, value_type):
            return_value = super().value(key, default_value)
        else:
            return_value = super().value(key, default_value, value_type)
        if set_if_missing:
            if super().value(key) is None:
                self.setValue(key, return_value)
        return return_value


class StatusBar(QStatusBar):
    '''
    Simple status bar for displaying current state of application:
    - idle,
    - busy,
    - error occured
    and configuration check boxes.

    Qt method naming convention is preserved.

    :ivar _resources: Icons used as a depiction of current application'same
        state (may be animated)
    :ivar _labels: Labels displaying status: one for icon and one for text
        description
    :ivar _check_boxes: Check boxes for the user to customize application's
        behavior
    :ivar _settings: Settings object storing check boxes' configuration
    '''
    def __init__(self) -> None:
        super().__init__()
        # Get rid of size grip
        self.setSizeGripEnabled(False)
        # Load and prepare required resources
        self._resources = {
            'ok': QIcon('img/ok.png'),
            'error': QIcon('img/error.png'),
            'web_error': QIcon('img/web_error.png'),
            'db_error': QIcon('img/db_error.png'),
            'spinner': QMovie('img/spinner.gif')
        }
        self._resources['spinner'].setScaledSize(QSize(16, 16))
        self._resources['spinner'].start()
        # Create and configure needed labels
        self._labels = {
            'icon': QLabel(),
            'description': QLabel()
        }
        for label in self._labels.values():
            self.addWidget(label)
        # Create and configure needed check boxes
        self._check_boxes = {
            'restore_last_closed': CheckBox('Przywracaj ostatnio zamknięty urząd'),
            'update_only_current': QCheckBox('Aktualizuj tylko bieżący urząd')
        }
        for check_box in self._check_boxes.values():
            self.addPermanentWidget(check_box)
        self._settings: Optional[QSettings] = None

    def setSettings(self, settings: Optional[Settings]) -> None:
        '''
        Bind check boxes to the settings object storing their states.

        :param settings: Settings object for the check boxes to connect to
            (may be None to disable the check boxes)
        '''
        self._settings = settings
        if settings is not None:
            # If Settings object is provided, refresh it
            settings.sync()
            # Enable and update every check box
            for name, check_box in self._check_boxes.items():
                check_box.setChecked(settings.value(
                    'check_box/' + name, False, value_type=bool, set_if_missing=True))
                check_box.stateChanged.connect(partial(
                    lambda name, state: settings.setValue(
                        'check_box/' + name, bool(state)), name))
                check_box.setEnabled(True)
        else:
            # If Settings object is removed, freeze check boxes and clear
            # their callbacks
            for check_box in self._check_boxes.values():
                check_box.setEnabled(False)
                try:
                    check_box.stateChanged.disconnect()
                except TypeError:
                    # If nothing is connected to the signal, an exception will be
                    # raised
                    pass

    def showSuccess(self) -> None:
        '''
        Depict idle state of the app.
        '''
        for label in self._labels.values():
            label.show()
        self._labels['icon'].setPixmap(self._resources['ok'].pixmap(16, 16))
        self._labels['description'].setText('Gotowe.')

    def showBusy(self) -> None:
        '''
        Indicate occuring update of data (in cache or in GUI).
        '''
        for label in self._labels.values():
            label.show()
        self._labels['icon'].setMovie(self._resources['spinner'])
        self._labels['icon'].setFixedSize(16, 16)
        self._labels['description'].setText('Aktualizacja...')

    def showError(self, cause: Union[Exception, str]) -> None:
        '''
        Show error message or exception in status bar.

        :param cause: Exception or error message to be displayed in status bar
        '''
        for label in self._labels.values():
            label.show()
        if isinstance(cause, APIError):
            # API-related error
            self._labels['icon'].setPixmap(
                self._resources['web_error'].pixmap(16, 16))
            self._labels['description'].setText('Błąd: ' + str(cause))
        elif isinstance(cause, DatabaseError):
            # Cache-related error
            self._labels['icon'].setPixmap(
                self._resources['db_error'].pixmap(16, 16))
            self._labels['description'].setText('Błąd: ' + str(cause))
        else:
            # Other errors
            self._labels['icon'].setPixmap(
                self._resources['error'].pixmap(16, 16))
            self._labels['description'].setText('Błąd: ' + str(cause))

    def clearState(self) -> None:
        '''
        Reset and hide status bar's labels.
        '''
        for label in self._labels.values():
            label.setText('')
            label.hide()


class CheckBox(QCheckBox):
    def __init__(self, text: str, initial_state: bool = False) -> None:
        super().__init__(text)
        self.setChecked(initial_state)
        self._user_data = None

    def userData(self) -> Any:
        '''
        Get user data associated with the check box.

        :returns: Arbitrary user data assigned to the check box
        '''
        return self._user_data

    def setUserData(self, data: Any) -> None:
        '''
        Associate user data with the check box.

        :param data: Arbitrary user data to be assigned to the check_box
        '''
        self._user_data = data


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
        '''
        Run the thread.
        (internal function)
        '''
        try:
            self._api.update()
            self.succeeded.emit()
        except Exception as exc:
            self.failed.emit(exc)


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
    gotMatter: pyqtSignal = pyqtSignal(int, dict, QColor)
    gotMatterCount: pyqtSignal = pyqtSignal(int)
    succeeded: pyqtSignal = pyqtSignal()
    failed: pyqtSignal = pyqtSignal(Exception)

    def __init__(self, api: CachedAPI) -> None:
        super().__init__()
        self._api: CachedAPI = api

    def run(self) -> None:
        '''
        Run the thread.
        (internal function)
        '''
        try:
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
            self.succeeded.emit()
        except Exception as exc:
            self.failed.emit(exc)


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
    gotSampleList: pyqtSignal = pyqtSignal(int, list)
    succeeded: pyqtSignal = pyqtSignal()
    failed: pyqtSignal = pyqtSignal(Exception)

    def __init__(self, api: CachedAPI, chart: QueueSystemChart) -> None:
        super().__init__()
        self._api: CachedAPI = api
        self._chart: QueueSystemChart = chart

    def run(self) -> None:
        '''
        Run the thread.
        (internal function)
        '''
        try:
            matter_key_list = map(
                lambda series: series.userData(), self._chart.series())
            for index, matter_key in enumerate(matter_key_list):
                if matter_key is not None:
                    sample_list = self._api.get_sample_list(
                        matter_key['ordinal'], matter_key['group_id'])
                    self.gotSampleList.emit(index, sample_list)
            self.succeeded.emit()
        except Exception as exc:
            self.failed.emit(exc)


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
    :ivar _settings: Window's configuration file object
    :ivar _status: Window's status bar containing application state
        description and basic settings
    :ivar _table: Window's table of administrative matters object
    :ivar _threads: Window's dictionary of threads used for updating API
        and GUI data
    :ivar _timer: Window's API call timer
    '''
    def __init__(self, api: CachedAPI, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._api: CachedAPI = api
        # Configure settings file and load saved application's settings:
        # window's size and position
        self._settings: Settings = Settings()
        self.resize(self._settings.value('window/size', QSize(750, 580), set_if_missing=True))
        self.move(self._settings.value('window/position', self.pos(), set_if_missing=True))
        # Create ComboBox object
        self._combo: ComboBox = ComboBox()
        # Create and setup chart and its view
        self._chart: QueueSystemChart = QueueSystemChart()
        chart_view = QChartView()
        chart_view.setChart(self._chart)
        chart_view.setRenderHint(QPainter.Antialiasing)
        # Create the table
        self._table: QueueSystemTable = QueueSystemTable()
        # Create the status bar for the window
        self._status: StatusBar = StatusBar()
        self._status.setSettings(self._settings)
        self.setStatusBar(self._status)
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
        self._timer.setInterval(api.cooldown * 1000)
        # Create the dictionary of threads
        self._threads: Dict[str, QThread] = {
            'caching': CacheThread(api),
            'displaying': GUIUpdateThread(api, self._chart),
            'setting': GUISetupThread(api)
        }
        # Connect caching thread's started signal to functions indicating
        # busyness of the application
        self._threads['caching'].started.connect(lambda: self.setCursor(Qt.BusyCursor))
        self._threads['caching'].started.connect(self._status.showBusy)
        # Connect all threads' failed signals to exception logging function
        # and all threads' finished signals to the function "debusying" mouse
        # cursor
        for thread in self._threads.values():
            thread.failed.connect(self._print_exception)
            thread.failed.connect(self._status.showError)
            thread.finished.connect(self.unsetCursor)
        # Connect GUI threads' succeeded signals to the status bar's success
        # showing method
        self._threads['displaying'].succeeded.connect(self._status.showSuccess)
        self._threads['setting'].succeeded.connect(self._status.showSuccess)
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
            # If nothing is connected to the signal, an exception will be
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
            # If nothing is connected to the signal, an exception will be
            # raised
            pass
        # Reconnect succeeded signal to the GUI update thread
        self._threads['caching'].succeeded.connect(
            self._threads['displaying'].start)
        # Cache and display queue system data
        self._threads['caching'].start()
        # Start timer again in order to update the widgets cyclically
        self._timer.start()

    def resizeEvent(self, event: QResizeEvent) -> None:
        super().resizeEvent(event)
        self._settings.setValue('window/size', self.size())

    def moveEvent(self, event: QMoveEvent) -> None:
        super().moveEvent(event)
        self._settings.setValue('window/position', self.pos())

    def _print_exception(self, exception: Exception) -> None:
        print('Exception occured in GUI subthreads:')
        print(exception)

    def close(self) -> None:
        '''
        Close the window and clean up.
        (internal function)
        '''
        # Make sure the configuration is saved
        self._settings.sync()
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
    def settings(self) -> QSettings:
        '''
        Window's settings
        '''
        return self._settings

    @property
    def timer(self) -> QTimer:
        '''
        Window's timer
        '''
        return self._timer
