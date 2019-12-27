import sqlite3


connection = sqlite3.connect('cache.db')
cursor = connection.cursor()

cursor.execute('''
    CREATE TABLE IF NOT EXISTS offices (
        id TEXT NOT NULL PRIMARY KEY,
        name TEXT
    )
''')

cursor.execute('''
    CREATE TABLE IF NOT EXISTS matters (
        id INTEGER NOT NULL PRIMARY KEY,
        name TEXT,
        office_id TEXT NOT NULL,
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

cursor.commit()

cursor.execute('''
    DELETE FROM samples
    WHERE DATETIME(time) < DATETIME('now', 'localtime', '-1 hour')
''')

cursor.execute('''
    SELECT *
    FROM offices
''')

cursor.execute('''
    SELECT *
    FROM matters
''')

cursor.execute('''
    SELECT *
    FROM samples
''')

cursor.execute('''
    INSERT INTO 
''')

connection.close()
