import sqlite3
from api import WSStoreAPI, APIError


class SQLite3Cursor:
    def __init__(self, *args, **kwargs):
        self._args = args
        self._kwargs = kwargs

    def __enter__(self):
        self._connection = sqlite3.connect(*self._args, *self._kwargs)
        self._connection.row_factory = sqlite3.Row
        return self._connection.cursor()

    def __exit__(self, exc_type, exc_value, exc_traceback):
        if exc_type is None and exc_value is None and exc_traceback is None:
            self._connection.commit()
        else:
            self._connection.rollback()
        self._connection.close()
        return False


class CachedAPI(WSStoreAPI):
    def __init__(self, base_api_urls=None, cache_filename=':memory:'):
        super().__init__(base_api_urls)
        self._filename = cache_filename
        self._init_tables()

    def _init_tables(self):
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
        self._remove_old_samples()

    def _remove_old_samples(self):
        with SQLite3Cursor(self._filename) as cursor:
            cursor.execute('''
                DELETE FROM samples
                WHERE DATETIME(time, 'utc') < DATETIME('now', '-1 hour')
            ''')

    def _get_office_id(self, office_key):
        # checking argument's validity
        if type(office_key) is not str:
            raise TypeError('Office key has to be of type str')
        # checking database for matching office entry
        with SQLite3Cursor(self._filename) as cursor:
            office_id = cursor.execute('''
                SELECT id
                FROM offices
                WHERE key = ?
            ''', (office_key, )).fetchone()
        # returning found office ID (or None on failure)
        if office_id is None:
            return None
        else:
            return office_id[0]

    def _get_matter_id(self, matter_ordinal, matter_group_id, office_key=None):
        if office_key is None:
            office_key = self._office_key
        # checking arguments' validity
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
        # checking database for matching matter entry
        with SQLite3Cursor(self._filename) as cursor:
            office_id = self._get_office_id(office_key)
            if matter_ordinal is None:
                matter_id = cursor.execute('''
                    SELECT id
                    FROM matters
                    WHERE ordinal IS NULL AND group_id = ? AND office_id = ?
                ''', (matter_group_id, office_id)).fetchone()
            else:
                matter_id = cursor.execute('''
                    SELECT id
                    FROM matters
                    WHERE ordinal = ? AND group_id = ? AND office_id = ?
                ''', (matter_ordinal, matter_group_id, office_id)).fetchone()
        # returning found matter ID (or None on failure)
        if matter_id is None:
            return None
        else:
            return matter_id[0]

    def _check_if_sample_exists(self, time, matter_id):
        # checking arguments' validity
        if type(time) is not str:
            raise TypeError('Time has to be of type str')
        # checking database for matching matter entry
        with SQLite3Cursor(self._filename) as cursor:
            result = cursor.execute('''
                SELECT COUNT(*)
                FROM samples
                WHERE time = ? AND matter_id = ?
            ''', (time, matter_id)).fetchone()
        # returning found matter ID (or None on failure)
        if result[0] == 0:
            return False
        else:
            return True

    def get_office_list(self, office_key=None) -> list:
        if office_key is None:
            office_key = self._office_key
        with SQLite3Cursor(self._filename) as cursor:
            result = cursor.execute('''
                SELECT name, key
                FROM offices
                ORDER BY name
            ''')
            result_list = [{'name': name, 'key': key} for name, key in result]
        return result_list

    def get_matter_list(self, office_key=None) -> list:
        if office_key is None:
            office_key = self._office_key
        office_id = self._get_office_id(office_key)
        with SQLite3Cursor(self._filename) as cursor:
            result = cursor.execute('''
                SELECT name, ordinal, group_id
                FROM matters
                WHERE office_id = ?
                ORDER BY name
            ''', (office_id, ))
            result_list = [{
                'name': str(name),
                'ordinal': int(ordinal) if ordinal is not None else None,
                'group_id': int(group_id)
            } for name, ordinal, group_id in result
            ]
        return result_list

    def get_sample_list(self, matter_ordinal, matter_group_id, office_key=None) -> list:
        matter_id = self._get_matter_id(matter_ordinal, matter_group_id, office_key)
        with SQLite3Cursor(self._filename) as cursor:
            result = cursor.execute('''
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
            } for queue_length, open_counters, current_number, time in result
            ]
        return result_list

    def _store_office_list(self, office_list: list):
        with SQLite3Cursor(self._filename) as cursor:
            cursor.executemany('''
                INSERT INTO offices (name, key)
                VALUES (?, ?)
            ''', [(office['name'], office['key']) for office in office_list])

    def _store_matter(self, office_id, matter: dict):
        with SQLite3Cursor(self._filename) as cursor:
            cursor.execute('''
                INSERT INTO matters (name, ordinal, group_id, office_id)
                VALUES (?, ?, ?, ?)
                ''', (
                matter['name'],
                matter['ordinal'],
                matter['group_id'],
                office_id
                )
            )
            return cursor.lastrowid

    def _store_matter_list(self, office_key: str, matter_list: list):
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

    def _store_sample(self, matter_id, sample):
        with SQLite3Cursor(self._filename) as cursor:
            cursor.execute('''
                INSERT INTO samples (time, open_counters, queue_length,
                current_number, matter_id)
                VALUES (?, ?, ?, ?, ?)
            ''', (
                sample['time'],
                sample['open_counters'],
                sample['queue_length'],
                sample['current_number'],
                matter_id
            ))

    def _store_sample_list(self, office_key: str, matter_ordinal, matter_group_id, sample_list: list):
        matter_id = self._get_matter_id(office_key, matter_ordinal, matter_group_id)
        with SQLite3Cursor(self._filename) as cursor:
            cursor.executemany('''
                INSERT INTO samples (time, open_counters, queue_length,
                current_number, matter_id)
                VALUES (?, ?, ?, ?, ?)
            ''', [(
                sample['time'],
                sample['open_counters'],
                sample['queue_length'],
                sample['current_number'],
                matter_id
            ) for sample in sample_list]
            )

    def update(self):
        matters_with_samples = self.get_matters_with_samples()
        office_id = self._get_office_id(self._office_key)
        for matter in matters_with_samples:
            matter_id = self._get_matter_id(matter['ordinal'], matter['group_id'])
            if matter_id is None:
                matter_id = self._store_matter(office_id, matter)
            if not self._check_if_sample_exists(matter['time'], matter_id):
                self._store_sample(matter_id, matter)

    @property
    def office_key(self):
        return self._office_key

    @office_key.setter
    def office_key(self, value):
        if type(value) is str:
            self._office_key = value
        else:
            raise TypeError('Office key must be a string')
