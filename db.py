import time
import sqlite3

class DownloadHistory:
    def __init__(self, db_file):
        self.conn = sqlite3.connect(db_file)
        self.c = self.conn.cursor()
        self.c.execute('''CREATE TABLE IF NOT EXISTS download_history
                          (name text PRIMARY KEY, timestamp real)''')
        self.conn.commit()

    def __del__(self):
        self.conn.close()

    def insert(self, name, timestamp=None):
        if timestamp is None:
            timestamp = time.time()
        self.c.execute("INSERT INTO download_history VALUES (?, ?)", (name, timestamp))
        self.conn.commit()

    def update(self, name, timestamp):
        self.c.execute("UPDATE download_history SET timestamp=? WHERE name=?", (timestamp, name))
        self.conn.commit()

    def remove(self, name):
        self.c.execute("DELETE FROM download_history WHERE name=?", (name,))
        self.conn.commit()

    def get_all(self):
        self.c.execute("SELECT * FROM download_history")
        return [{'name': row[0], 'timestamp': row[1]} for row in self.c.fetchall()]
    
    def contains(self, name):
        self.c.execute("SELECT * FROM download_history WHERE name=?", (name,))
        return len(self.c.fetchall()) > 0


