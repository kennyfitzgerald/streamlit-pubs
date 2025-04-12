import sqlite3

# Create or connect to an SQLite database
conn = sqlite3.connect('geezers.db')
c = conn.cursor()

# Create a table for the pubs with updated columns and pint_price as REAL
c.execute('''
CREATE TABLE IF NOT EXISTS pubs (
    name TEXT,
    latitude REAL,
    longitude REAL,
    pool_table TEXT,
    darts TEXT,
    commentary TEXT,
    fosters_carling TEXT,
    pint_price REAL,
    lock_ins TEXT
);
''')

# Insert some example data (skip this if the table already has data)
# Here we insert a sample pint price as a float (e.g., 5.00)
c.execute(
    "INSERT INTO pubs (name, latitude, longitude, pool_table, darts, commentary, fosters_carling, pint_price, lock_ins) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
    ('The Station House', 51.586, -0.071, 'Yes', 'Yes', 'They get it', 'Yes', 5.00, 'Yes')
)

# Commit changes and close the connection
conn.commit()
conn.close()
