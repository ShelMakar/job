import sqlite3

conn = sqlite3.connect('mydatabase.db')
c = conn.cursor()

c.execute('''CREATE TABLE users
             (id INTEGER PRIMARY KEY,
              email TEXT UNIQUE NOT NULL,
              password TEXT NOT NULL,
              referral_code TEXT,
              referral_code_expiry TIMESTAMP)''')
c.execute('''CREATE TABLE referrals
             (id INTEGER PRIMARY KEY,
              user_id INTEGER NOT NULL,
              referrer_id INTEGER NOT NULL,
              FOREIGN KEY(user_id) REFERENCES users(id),
              FOREIGN KEY(referrer_id) REFERENCES users(id))''')

conn.commit()
conn.close()