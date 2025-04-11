import sqlite3

# Create or connect to an SQLite database
conn = sqlite3.connect('geezers.db')
c = conn.cursor()

# Create a table for the pubs
c.execute('''
CREATE TABLE IF NOT EXISTS pubs (
    name TEXT,
    latitude REAL,
    longitude REAL,
    rating REAL
);
''')

# Insert some example data (you can skip this if the table already has data)
c.execute("INSERT INTO pubs (name, latitude, longitude, rating) VALUES (?, ?, ?, ?)", 
          ('The Station House', 51.586,	-0.071, 4.5))

# Commit and close
conn.commit()
conn.close()
