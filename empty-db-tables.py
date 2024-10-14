import sqlite3

from database import DATABASE_URL


def empty_database(db_path):
    # Connect to the SQLite database
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Get the list of all tables in the database
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()

    # Iterate over all tables and delete their data
    for table in tables:
        table_name = table[0]
        if table_name != "sqlite_sequence":  # Avoid touching internal SQLite table used for auto-increment
            cursor.execute(f"DELETE FROM {table_name};")
            print(f"Emptied table: {table_name}")

    # Commit changes and close the connection
    conn.commit()
    conn.close()

if __name__ == "__main__":
    # Provide the path to your SQLite database file from DATABASE_URL
    db_path = DATABASE_URL.split("///")[-1]  # Extract the actual path from DATABASE_URL
    empty_database(db_path)
    print("Database has been emptied.")
