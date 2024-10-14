import os
import sqlite3

from dotenv import load_dotenv
from fastapi import FastAPI, Form, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, RedirectResponse
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

# Helper function to get the logged-in user
def get_logged_in_user(request: Request):
    user_id = request.session.get('user_id')
    if not user_id:
        return None
    conn = get_db_connection()
    user = conn.execute('SELECT * FROM users WHERE userid = ?', (user_id,)).fetchone()
    conn.close()
    return user

# Routes

@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    user = get_logged_in_user(request)
    return templates.TemplateResponse("index.html", {"request": request, "user": user})

@app.get("/dashboard/", response_class=HTMLResponse)
async def dashboard(request: Request):
    user = get_logged_in_user(request)
    if not user:
        return RedirectResponse(url="/login/", status_code=303)  # Redirect to login page if not authenticated
    return templates.TemplateResponse("dashboard.html", {"request": request, "user": user})

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
        return RedirectResponse(url="/dashboard/", status_code=303)  # Redirect to dashboard
    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

@app.get("/logout/")
async def logout(request: Request):
    # Clear the user session
    request.session.pop('user_id', None)  # Remove the user ID from the session
    return RedirectResponse(url="/login/", status_code=303)

# Protected routes

@app.get("/users/", response_class=HTMLResponse)
async def get_users(request: Request):
    user = get_logged_in_user(request)
    if not user:
        return RedirectResponse(url="/login/", status_code=303)  # Redirect to login page if not authenticated

    conn = get_db_connection()
    users = conn.execute('SELECT * FROM users').fetchall()
    conn.close()
    return templates.TemplateResponse("users.html", {"request": request, "users": users, "user": user})

@app.get("/add-user/", response_class=HTMLResponse)
async def add_user_form(request: Request):
    user = get_logged_in_user(request)
    if not user:
        return RedirectResponse(url="/login/", status_code=303)  # Redirect to login page if not authenticated
    return templates.TemplateResponse("add_user.html", {"request": request, "user": user})

@app.post("/add-user/")
async def add_user(request: Request, username: str = Form(...), password: str = Form(...)):
    user = get_logged_in_user(request)
    if not user:
        return RedirectResponse(url="/login/", status_code=303)  # Redirect to login page if not authenticated

    conn = get_db_connection()
    try:
        conn.execute('INSERT INTO users (username, password) VALUES (?, ?)', (username, password))
        conn.commit()
    except sqlite3.IntegrityError:
        conn.close()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="User already exists.")
    conn.close()
    return RedirectResponse(url="/users/", status_code=303)

@app.get("/modify-user/{userid}/", response_class=HTMLResponse)
async def modify_user(request: Request, userid: int):
    user = get_logged_in_user(request)
    if not user:
        return RedirectResponse(url="/login/", status_code=303)  # Redirect to login page if not authenticated

    conn = get_db_connection()
    target_user = conn.execute('SELECT * FROM users WHERE userid = ?', (userid,)).fetchone()
    conn.close()
    if target_user:
        return templates.TemplateResponse("modify_user.html", {"request": request, "user": user, "target_user": target_user})
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

@app.post("/modify-user/{userid}/")
async def modify_user_post(request: Request, userid: int, username: str = Form(...), password: str = Form(...)):
    user = get_logged_in_user(request)
    if not user:
        return RedirectResponse(url="/login/", status_code=303)  # Redirect to login page if not authenticated

    conn = get_db_connection()
    conn.execute('UPDATE users SET username = ?, password = ? WHERE userid = ?', (username, password, userid))
    conn.commit()
    conn.close()
    return RedirectResponse(url="/users/", status_code=303)

@app.get("/delete-user/{userid}/")
async def delete_user(request: Request, userid: int):
    user = get_logged_in_user(request)
    if not user:
        return RedirectResponse(url="/login/", status_code=303)  # Redirect to login page if not authenticated

    conn = get_db_connection()
    conn.execute('DELETE FROM users WHERE userid = ?', (userid,))
    conn.commit()
    conn.close()
    return RedirectResponse(url="/users/", status_code=303)
