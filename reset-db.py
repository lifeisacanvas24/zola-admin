import os
import sqlite3

from passlib.hash import pbkdf2_sha256

# Load your secret key from the environment
secret_key = os.getenv("SECRET_KEY", "default_secret_key")

def hash_password(password: str) -> str:
    # Combine password and secret key for hashing
    salted_password = password.encode('utf-8') + secret_key.encode('utf-8')
    # Use PBKDF2 with the combined salted password
    return pbkdf2_sha256.using(rounds=100000).hash(salted_password)

def create_database():
    # Connect to the database (or create it)
    conn = sqlite3.connect('zolanew_admin.db')
    cursor = conn.cursor()

    # Create users table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            userid INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL
        )
    ''')

    # Hash the default admin password
    admin_username = "admin"
    admin_password = "admin"
    hashed_password = hash_password(admin_password)

    # Insert default admin user
    try:
        cursor.execute('INSERT INTO users (username, password) VALUES (?, ?)', (admin_username, hashed_password))
        conn.commit()
        print("Default admin user created.")
    except sqlite3.IntegrityError:
        print("Admin user already exists.")

    # Close the connection
    conn.close()

if __name__ == "__main__":
    create_database()
