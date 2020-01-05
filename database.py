import sqlite3
import api


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


def init_tables(cursor):
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS offices (
            id INTEGER PRIMARY KEY,
            name TEXT,
            key TEXT
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
                REFERENCES offices (id)
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS samples (
            time TEXT NOT NULL,
            matter_id INTEGER NOT NULL,
            open_counters INTEGER,
            queue_length INTEGER,
            PRIMARY KEY (time, matter_id),
            FOREIGN KEY (matter_id)
                REFERENCES matters (id)
        )
    ''')
    cursor.execute('''
        DELETE FROM samples
        WHERE DATETIME(time, 'utc') < DATETIME('now', '-1 hour')
    ''')


def get_office_list(cursor):
    result = cursor.execute('''
        SELECT name, key
        FROM offices
        ORDER BY name
    ''')
    cached_list = [{'name': name, 'key': key} for name, key in result]
    if len(cached_list) == 0:
        office_list = api.get_office_list()
        store_office_list(cursor, office_list)
        return office_list
    else:
        return cached_list


def store_office_list(cursor, office_list):
    cursor.executemany('''
        INSERT INTO offices (name, key)
        VALUES (?, ?)
    ''', [(office['name'], office['key']) for office in office_list])


def get_matter_list(cursor, office_key):
    return api.get_matter_list(office_key)
    # cursor.execute('''
    #     SELECT *
    #     FROM matters
    #     WHERE office_id = ?
    #     ORDER BY name
    # ''', (int, ))


def store_matter_list(office_key):
    pass
    # cursor.execute('''
    #     INSERT INTO offices (name, ordinal, group_id, office_id)
    #     VALUES (?, ?, ?, ?)
    # ''', (str, int/None, int, int))


def get_time_samples(matter_id):
    pass
    # cursor.execute('''
    #     SELECT MAX(time)
    #     FROM samples
    #     WHERE matter_id = ?
    # ''', (int, ))

    # cursor.execute('''
    #     SELECT (STRFTIME('%s', ?) - STRFTIME('%s', time)) / 60 AS index,
    #         open_counters, queue_length
    #     FROM samples
    #     WHERE matter_id = ?
    #     ORDER BY index
    # ''', (str, int))


def store_time_sample(matter_id, data):
    pass
    # cursor.execute('''
    #     INSERT INTO samples
    #     VALUES (?, ?, ?, ?)
    # ''', (str, int, int, int))
