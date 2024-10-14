import os
import sqlite3

from dotenv import load_dotenv
from fastapi import FastAPI, Form, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware

# Load environment variables
load_dotenv()

# Initialize FastAPI app
app = FastAPI()

# Configure session middleware
secret_key = os.getenv("SECRET_KEY", "default_secret_key")
app.add_middleware(SessionMiddleware, secret_key=secret_key)

# CORS middleware if needed
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure Jinja2 templates
templates = Jinja2Templates(directory="templates")

# Mount static files directory
app.mount("/static", StaticFiles(directory="static"), name="static")

# Database connection
def get_db_connection():
    conn = sqlite3.connect('zolanew_admin.db')
    conn.row_factory = sqlite3.Row
    return conn

@app.get("/users/", response_class=HTMLResponse)
async def get_users(request: Request):
    conn = get_db_connection()
    users = conn.execute('SELECT * FROM users').fetchall()
    conn.close()
    return templates.TemplateResponse("users.html", {"request": request, "users": users})

@app.post("/add-user/")
async def add_user(request: Request, username: str = Form(...), password: str = Form(...)):
    conn = get_db_connection()
    try:
        # Store password securely in production
        conn.execute('INSERT INTO users (username, password) VALUES (?, ?)', (username, password))
        conn.commit()
    except sqlite3.IntegrityError:
        conn.close()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="User already exists.")
    conn.close()
    return {"message": "User added!"}

@app.post("/modify-user/{userid}/")
async def modify_user(request: Request, userid: int, username: str = Form(...), password: str = Form(...)):
    conn = get_db_connection()
    try:
        conn.execute('UPDATE users SET username = ?, password = ? WHERE userid = ?', (username, password, userid))
        conn.commit()
    except sqlite3.Error:
        conn.close()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Failed to update user.")
    conn.close()
    return {"message": "User updated!"}

@app.get("/login/", response_class=HTMLResponse)
async def login(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@app.post("/login/")
async def login_post(request: Request, username: str = Form(...), password: str = Form(...)):
    conn = get_db_connection()
    user = conn.execute('SELECT * FROM users WHERE username = ? AND password = ?', (username, password)).fetchone()
    conn.close()
    if user:
        request.session['user_id'] = user['userid']  # Store user ID in session
        return {"message": "Login successful!"}  # Redirect to the users page or dashboard
    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

@app.get("/logout/")
async def logout(request: Request):
    # Clear the user session
    request.session.pop('user_id', None)  # Remove the user ID from the session
    return {"message": "Logout successful!"}  # You can redirect to the login page or home page if desired

@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

# Create admin user if not exists
def create_admin_user():
    conn = get_db_connection()
    conn.execute('CREATE TABLE IF NOT EXISTS users (userid INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT UNIQUE, password TEXT)')
    try:
        conn.execute('INSERT INTO users (username, password) VALUES (?, ?)', ("admin", "admin"))  # Change this for security
        conn.commit()
    except sqlite3.IntegrityError:
        pass  # Admin user already exists
    conn.close()

create_admin_user()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
