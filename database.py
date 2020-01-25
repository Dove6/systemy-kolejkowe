import sqlite3
from api import WSStoreAPI

from types import TracebackType
from typing import Union, Optional, Dict, List, Tuple, Any
from retrying import retry

from api import OfficeData, OfficeList
MatterData = Dict[str, Union[str, Optional[int]]]
MatterList = List[MatterData]
SampleData = Dict[str, Union[str, int]]
SampleList = List[SampleData]


class SQLite3Cursor:
    '''
    Context manager for opening and automatically closing sqlite3 database
    connection

    If any exceptions are thrown, the manager rollbacks changes to database,
    else the changes are commited.

    For arguments reference, see sqlite3.connect

    :param `*args`: Positional arguments to be passed to sqlite3.connect
    :param `*kwargs`: Named arguments to be passed to sqlite3.connect
    :ivar args: Positional arguments to be passed to sqlite3.connect
    :ivar kwargs: Named arguments to be passed to sqlite3.connect
    :ivar connection: SQLite3 connection object created upon entering
        the context
    '''
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        self._args: Tuple[Any, ...] = args
        self._kwargs: Dict[str, Any] = kwargs
        self._connection: Optional[sqlite3.Connection] = None

    def __enter__(self) -> sqlite3.Cursor:
        '''
        Initialize context.
        (internal function)

        Opened connection's curson is returned for "as" keyword.
        '''
        self._connection = sqlite3.connect(*self._args, *self._kwargs)
        self._connection.row_factory = sqlite3.Row
        return self._connection.cursor()

    def __exit__(
            self, exc_type: Optional[type],
            exc_value: Any,
            exc_traceback: Optional[TracebackType]) -> bool:
        '''
        Clean-up context.
        (internal function)

        Function doesn't silence exceptions.

        :param exc_type: Exception type
        :param exc_value: Exception value
        :param exc_traceback: Exception traceback
        '''
        if exc_type is None and exc_value is None and exc_traceback is None:
            self._connection.commit()
        else:
            self._connection.rollback()
        self._connection.close()
        return False


class DatabaseError(Exception):
    '''
    Exception indicating errors during accessing the underlying database.
    '''
    pass


class CachedAPI(WSStoreAPI):
    '''
    Subclass of WWStoreApi, which caches fetched data using an SQLite3
    database file.

    :param html_api_url: Base URL of API returning HTML encoded data
    :param json_api_url: Base URL of API returning JSON encoded data
    :param cache_filename: SQLite3 database filename (defaults to ':memory:')
    :ivar _api_urls: Base URLs of APIs provided in constructor
    :ivar _office_key: Default office identifier (settable through
        self.office_key property)
    :ivar _filename: SQLite3 database filename provided in constructor
    :ivar _cooldown: Minimal interval between API calls in seconds (default
        value equals 60, settable through self.cooldown property)
    '''
    def __init__(
            self, html_api_url: str, json_api_url: str,
            cache_filename: Optional[str] = None) -> None:
        super().__init__(html_api_url, json_api_url)
        if cache_filename is None:
            self._filename: str = ':memory:'
        else:
            self._filename: str = cache_filename
        self._init_tables()
        self._remove_old_samples()
        self._cooldown: int = 60

    #
    # Methods called during initialization
    #

    def _init_tables(self) -> None:
        '''
        Create required database tables if they are non-existent.
        (internal function)
        '''
        with SQLite3Cursor(self._filename) as cursor:
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS offices (
                    id INTEGER PRIMARY KEY,
                    name TEXT,
                    key TEXT UNIQUE
                )
            ''')
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS matters (
                    id INTEGER PRIMARY KEY,
                    name TEXT,
                    ordinal INT,
                    group_id INT,
                    office_id INTEGER NOT NULL,
                    FOREIGN KEY (office_id)
                        REFERENCES offices (id),
                    UNIQUE (ordinal, group_id, office_id)
                )
            ''')
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS samples (
                    time TEXT NOT NULL,
                    matter_id INTEGER NOT NULL,
                    open_counters INTEGER,
                    queue_length INTEGER,
                    current_number TEXT,
                    PRIMARY KEY (time, matter_id),
                    FOREIGN KEY (matter_id)
                        REFERENCES matters (id)
                )
            ''')
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS last_connection (
                    office_id INTEGER PRIMARY KEY,
                    time TEXT,
                    FOREIGN KEY (office_id)
                        REFERENCES offices (id)
                )
            ''')

    def _remove_old_samples(self) -> None:
        '''
        Remove queue state data older than from 1 hour before.
        (internal function)
        '''
        with SQLite3Cursor(self._filename) as cursor:
            cursor.execute('''
                DELETE FROM samples
                WHERE DATETIME(time, 'utc') < DATETIME('now', '-1 hour')
            ''')

    #
    # Private methods used internally
    #

    def _get_office_id(
            self, office_key: Optional[str] = None) -> Optional[int]:
        '''
        Get ID number representing an office with a given key in the local
        database.
        (internal function)

        :param office_key: Requested office's key identifier (defaults
            to self.office_key)
        :returns: Corresponding office's ID number (if present)
        '''
        if office_key is None:
            office_key = self._office_key
        # Check argument's validity
        if office_key is None:
            raise AssertionError('Office key not provided')
        if type(office_key) is not str:
            raise TypeError('Office key has to be of type str')
        # Check database for matching office entry
        with SQLite3Cursor(self._filename) as cursor:
            office_id = cursor.execute('''
                SELECT id
                FROM offices
                WHERE key = ?
            ''', (office_key, )).fetchone()
        # Return found office ID (or None on failure)
        if office_id is None:
            return None
        else:
            return office_id[0]

    def _get_matter_id(
            self, matter_ordinal: Optional[int], matter_group_id: int,
            office_key: Optional[str] = None) -> Optional[int]:
        '''
        Get ID number representing an administrative matter with given
        details in the local database.
        (internal function)

        :param matter_ordinal: Requested matter's ordinal number
        :param matter_group_id: Requested matter's group ID
        :param office_key: Key identifier of an office the matter belongs to
            (defaults to self.office_key)
        :returns: Corresponding administrative matter's ID number (if present)
        '''
        if office_key is None:
            office_key = self._office_key
        # Check arguments' validity
        if office_key is None:
            raise AssertionError('Office key not provided')
        if type(matter_ordinal) not in [int, type(None)]:
            try:
                matter_ordinal = int(matter_ordinal)
            except (ValueError, TypeError):
                raise TypeError("Non-None matter's ordinal must be convertible to int")
        if type(matter_group_id) is not int:
            try:
                matter_group_id = int(matter_group_id)
            except (ValueError, TypeError):
                raise TypeError("Matter's group's ID must be convertible to int")
        # Check database for matching matter entry
        office_id = self._get_office_id(office_key)
        with SQLite3Cursor(self._filename) as cursor:
            if matter_ordinal is None:
                matter_id = cursor.execute(
                    '''
                    SELECT id
                    FROM matters
                    WHERE ordinal IS NULL AND group_id = ? AND office_id = ?
                    ''', (matter_group_id, office_id)
                ).fetchone()
            else:
                matter_id = cursor.execute(
                    '''
                    SELECT id
                    FROM matters
                    WHERE ordinal = ? AND group_id = ? AND office_id = ?
                    ''', (matter_ordinal, matter_group_id, office_id)
                ).fetchone()
        # Return found matter ID (or None on failure)
        if matter_id is None:
            return None
        else:
            return matter_id[0]

    def _check_if_sample_exists(self, time: str, matter_id: int) -> bool:
        '''
        Check if a time sample represented by a given primary key exists.
        (internal function)

        :param time: Requested sample's collection time
            (format: YYYY-MM-DD HH:MM)
        :param matter_id: ID of administrative matter requested sample
            belongs to
        :returns: True if a sample exists, False otherwise
        '''
        # Check arguments' validity
        if type(time) is not str:
            raise TypeError('Time has to be of type str')
        # Check database for matching matter entry
        with SQLite3Cursor(self._filename) as cursor:
            result = cursor.execute(
                '''
                SELECT COUNT(*)
                FROM samples
                WHERE time = ? AND matter_id = ?
                ''', (time, matter_id)
            ).fetchone()
        # Return found matter ID (or None on failure)
        if result[0] == 0:
            return False
        else:
            return True

    def _get_seconds_since_last_connection(
            self, office_key: Optional[str] = None) -> Optional[int]:
        '''
        Retrieve number of seconds since last API request.
        (internal function)

        :param office_key: Key identifier of an office which data were
            requested (defaults to self.office_key)
        :returns: Number of seconds since last API call (or None if such call
            hasn't been executed yet)
        '''
        if office_key is None:
            office_key = self._office_key
        # Check arguments' validity
        if office_key is None:
            raise AssertionError('Office key not provided')
        # Query database for difference in time since last connection
        # (in seconds)
        office_id = self._get_office_id(office_key)
        with SQLite3Cursor(self._filename) as cursor:
            cursor.execute('''
                SELECT (STRFTIME('%s', 'now', 'localtime')
                - STRFTIME('%s', time))
                FROM last_connection
                WHERE office_id = ?
                ''', (office_id,)
            )
            # Return result of query
            return cursor.fetchone()[0]

    def _update_last_connection_time(
            self, office_key: Optional[str] = None) -> None:
        '''
        Set time of last API connection to current time.
        (internal function)

        :param office_key: Key identifier of an office which data were
            requested (defaults to self.office_key)
        '''
        if office_key is None:
            office_key = self._office_key
        # Check arguments' validity
        if office_key is None:
            raise AssertionError('Office key not provided')
        # Update appropriate table row
        office_id = self._get_office_id(office_key)
        with SQLite3Cursor(self._filename) as cursor:
            cursor.execute(
                '''
                UPDATE last_connection
                SET time = DATETIME('now', 'localtime')
                WHERE office_id = ?
                ''', (office_id,))

    def _store_office_list(self, office_list: OfficeList) -> None:
        '''
        Place given list of office identifiers in cache.
        (internal function)
        '''
        with SQLite3Cursor(self._filename) as cursor:
            cursor.executemany(
                '''
                INSERT INTO offices (name, key)
                VALUES (?, ?)
                ''', [
                    (office['name'], office['key'])
                    for office in office_list
                ])
            # Prepare entries in last_connection table for storing time
            # of last API call
            office_ids = [
                (self._get_office_id(office['key']),)
                for office in office_list]
            cursor.executemany(
                '''
                INSERT INTO last_connection (office_id)
                VALUES (?)
                ''', office_ids)

    def _store_matter(self, office_id: int, matter: MatterData) -> int:
        '''
        Place a single matter description in cache.
        (internal function)

        :param office_id: ID number of cached representation of an office
            given administrative matter belongs to
        :param matter: Administrative matter's data
        :returns: ID number representing the matter in database after its
            addition
        '''
        with SQLite3Cursor(self._filename) as cursor:
            cursor.execute(
                '''
                INSERT INTO matters (name, ordinal, group_id, office_id)
                VALUES (?, ?, ?, ?)
                ''', (
                    matter['name'], matter['ordinal'], matter['group_id'],
                    office_id)
            )
            # ID of matter = ID of last modified row
            inserted_id = cursor.lastrowid
            return inserted_id

    def _store_matter_list(
            self, office_key: Optional[str], matter_list: MatterList) -> None:
        '''
        Place given list of administrative matters' descriptions in cache.
        (internal function)

        :param office_key: Key identifier of an office the matter belongs to
            (defaults to self.office_key)
        :param matter_list: List of matters' data to store
        '''
        if office_key is None:
            office_key = self._office_key
        # Check arguments' validity
        if office_key is None:
            raise AssertionError('Office key not provided')
        # Insert content of matters' list into database
        office_id = self._get_office_id(office_key)
        with SQLite3Cursor(self._filename) as cursor:
            cursor.executemany('''
                INSERT INTO matters (name, ordinal, group_id, office_id)
                VALUES (?, ?, ?, ?)
            ''', [(
                matter['name'],
                matter['ordinal'],
                matter['group_id'],
                office_id
            ) for matter in matter_list]
            )

    def _store_sample(self, matter_id: int, sample: SampleData) -> None:
        '''
        Place a single time sample in cache.
        (internal function)

        :param matter_id: ID number of cached representation of administrative
            matter given time sample belongs to
        :param sample: Time sample to be stored
        '''
        with SQLite3Cursor(self._filename) as cursor:
            cursor.execute(
                '''
                INSERT INTO samples (time, open_counters, queue_length,
                current_number, matter_id)
                VALUES (?, ?, ?, ?, ?)
                ''', (
                    sample['time'], sample['open_counters'],
                    sample['queue_length'], sample['current_number'],
                    matter_id))

    def _store_sample_list(
            self, office_key: Optional[str], matter_ordinal: Optional[int],
            matter_group_id: int, sample_list: SampleList) -> None:
        '''
        Place given list of time samples in cache.
        (internal function)

        :param office_key: Key identifier of an office the matter belongs to
            (defaults to self.office_key)
        :param matter_ordinal: Ordinal number of an administrative matter
            given samples are associated with
        :param matter_ordinal: Group ID of an administrative matter given
            samples are associated with
        :param matter_list: List of time samples to store
        '''
        matter_id = self._get_matter_id(office_key, matter_ordinal, matter_group_id)
        with SQLite3Cursor(self._filename) as cursor:
            cursor.executemany(
                '''
                INSERT INTO samples (time, open_counters, queue_length,
                current_number, matter_id)
                VALUES (?, ?, ?, ?, ?)
                ''', [(
                    sample['time'], sample['open_counters'],
                    sample['queue_length'], sample['current_number'],
                    matter_id) for sample in sample_list])

    #
    # Public methods
    #

    def get_office_list(self) -> OfficeList:
        '''
        Retrieve cached office identifiers list if available, otherwise
        fetch it using API.

        The list can be used to get office-specific data.

        :returns: Office identifiers list
        '''
        with SQLite3Cursor(self._filename) as cursor:
            result = cursor.execute(
                '''
                SELECT name, key
                FROM offices
                ORDER BY name
                ''')
            result_list = [{'name': name, 'key': key} for name, key in result]
        if len(result_list) != 0:
            return result_list
        else:
            # If nothing's in database, query the API
            result_list = super().get_office_list()
            self._store_office_list(result_list)
            return result_list

    def get_matter_list(
            self, office_key: Optional[str] = None) -> MatterList:
        '''
        Retrieve cached administrative matter list if available, otherwise
        fetch it using API.

        The list can be used to get matter-specific queue data.

        :returns: Administrative matter description list
        '''
        if office_key is None:
            office_key = self._office_key
        # Check arguments' validity
        if office_key is None:
            raise AssertionError('Office key not provided')
        # Query the database for matters
        office_id = self._get_office_id(office_key)
        with SQLite3Cursor(self._filename) as cursor:
            result = cursor.execute(
                '''
                SELECT name, ordinal, group_id
                FROM matters
                WHERE office_id = ?
                ORDER BY name
                ''', (office_id, ))
            result_list = [{
                'name': str(name),
                'ordinal': int(ordinal) if ordinal is not None else None,
                'group_id': int(group_id)
            } for name, ordinal, group_id in result]
        return result_list

    def get_sample_list(
            self, matter_ordinal: Optional[int], matter_group_id: int,
            office_key: Optional[str] = None) -> SampleList:
        '''
        Retrieve all cached time samples associated with given administrative
        matter.

        :param matter_ordinal: Requested matter's ordinal number
        :param matter_group_id: Requested matter's group ID
        :param office_key: Key identifier of an office the matter belongs to
            (defaults to self.office_key)
        :returns: List of time samples of queue connected with requested
            administrative matter
        '''
        matter_id = self._get_matter_id(matter_ordinal, matter_group_id, office_key)
        with SQLite3Cursor(self._filename) as cursor:
            result = cursor.execute(
                '''
                SELECT queue_length, open_counters, current_number, time
                FROM samples
                WHERE matter_id = ?
                ORDER BY time
                ''', (matter_id, ))
            result_list = [{
                'queue_length': int(queue_length),
                'open_counters': int(open_counters),
                'current_number': str(current_number),
                'time': str(time)
            } for queue_length, open_counters, current_number, time in result]
        return result_list

    def update(self) -> None:
        '''
        Get data from API and store them in cache.
        '''
        # Check time passed since last API call
        passed_time = self._get_seconds_since_last_connection()
        if passed_time > self._cooldown or passed_time is None:
            # If passed more than self._cooldown seconds or there is no
            # information about previous call, proceed with the update
            matters_with_samples = self.get_matters_with_samples()
            self._update_last_connection_time()
            office_id = self._get_office_id(self._office_key)
            for matter in matters_with_samples:
                matter_id = self._get_matter_id(matter['ordinal'], matter['group_id'])
                if matter_id is None:
                    matter_id = self._store_matter(office_id, matter)
                if not self._check_if_sample_exists(matter['time'], matter_id):
                    self._store_sample(matter_id, matter)

    #
    # Properties
    #

    @property
    def cooldown(self) -> int:
        '''
        Minimal interval between API calls in seconds.

        :raises: :class:`TypeError`: Trying to assign non-integer value
        '''
        return self._cooldown

    @cooldown.setter
    def cooldown(self, value: int) -> None:
        if type(value) is int:
            self._cooldown = value
            if value < 30:
                print('Warning: too short API polling interval')
        else:
            raise TypeError('Cooldown must be an integer')
