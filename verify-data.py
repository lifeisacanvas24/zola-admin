import sqlite3

# Connect to the SQLite database
conn = sqlite3.connect('zolanew_admin.db')  # Make sure this path is correct
cursor = conn.cursor()

# Query to select the admin user
cursor.execute("SELECT userid, username, password FROM users WHERE username = 'admin'")

# Fetch the result
admin_user = cursor.fetchone()

if admin_user:
    userid, username, password = admin_user
    print("Admin user found:")
    print(f"User ID: {userid}")
    print(f"Username: {username}")
    print(f"Password hash: {password}")
else:
    print("Admin user not found in the database.")

# Close the connection
conn.close()
