import sqlite3


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

def 
cursor.execute('''
    SELECT *
    FROM offices
    ORDER BY name
''')

cursor.execute('''
    INSERT INTO offices (name, key)
    VALUES (?, ?)
''', (str, str))


cursor.execute('''
    SELECT *
    FROM matters
    WHERE office_id = ?
    ORDER BY name
''', (int, ))

cursor.execute('''
    INSERT INTO offices (name, ordinal, group_id, office_id)
    VALUES (?, ?, ?, ?)
''', (str, int/None, int, int))


cursor.execute('''
    SELECT MAX(time)
    FROM samples
    WHERE matter_id = ?
''', (int, ))

cursor.execute('''
    SELECT (STRFTIME('%s', ?) - STRFTIME('%s', time)) / 60 AS index, 
        open_counters, queue_length
    FROM samples
    WHERE matter_id = ?
    ORDER BY index
''', (str, int))

cursor.execute('''
    DELETE FROM samples
    WHERE DATETIME(time) < DATETIME(?, '-1 hour')
''', (str, ))

cursor.execute('''
    INSERT INTO samples
    VALUES (?, ?, ?, ?)
''', (str, int, int, int))

connection.close()
