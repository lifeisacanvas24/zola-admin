import os
import sqlite3

from passlib.hash import pbkdf2_sha256

# Load your secret key from the environment (not required for passlib hashing)
secret_key = os.getenv("SECRET_KEY", "default_secret_key")

def hash_password(password: str) -> str:
    # Hash the password using pbkdf2_sha256 (passlib handles the salting securely)
    return pbkdf2_sha256.hash(password)

def verify_password(password: str, hashed_password: str) -> bool:
    # Verify the password using passlib's verify function
    return pbkdf2_sha256.verify(password, hashed_password)

def create_database():
    # Connect to the SQLite database (or create it if it doesn't exist)
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

    # Default admin credentials
    admin_username = "admin"
    admin_password = "admin"

    # Hash the admin password
    hashed_password = hash_password(admin_password)

    # Insert default admin user, or skip if already exists
    try:
        cursor.execute('INSERT INTO users (username, password) VALUES (?, ?)', (admin_username, hashed_password))
        conn.commit()
        print("Default admin user created.")
    except sqlite3.IntegrityError:
        print("Admin user already exists.")

    # Close the database connection
    conn.close()

if __name__ == "__main__":
    create_database()
