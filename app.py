import os
import sqlite3

from dotenv import load_dotenv
from fastapi import FastAPI, Form, HTTPException, Request, status, Depends
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

# Helper function to get the current logged-in user
def get_current_user(request: Request):
    user_id = request.session.get('user_id')
    if not user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authenticated")
    return user_id

@app.get("/users/", response_class=HTMLResponse)
async def get_users(request: Request, user_id: int = Depends(get_current_user)):
    conn = get_db_connection()
    users = conn.execute('SELECT * FROM users').fetchall()
    conn.close()

    success_message = request.session.pop('success_message', None)

    return templates.TemplateResponse("users.html", {"request": request, "users": users, "success_message": success_message})

@app.get("/add-user/", response_class=HTMLResponse)
async def add_user_form(request: Request, user_id: int = Depends(get_current_user)):
    return templates.TemplateResponse("add_user.html", {"request": request})

@app.post("/add-user/")
async def add_user(request: Request, username: str = Form(...), password: str = Form(...), user_id: int = Depends(get_current_user)):
    conn = get_db_connection()
    try:
        conn.execute('INSERT INTO users (username, password) VALUES (?, ?)', (username, password))
        conn.commit()
    except sqlite3.IntegrityError:
        conn.close()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="User already exists.")
    conn.close()

    request.session['success_message'] = "User added successfully!"
    return RedirectResponse(url="/users/", status_code=303)

@app.get("/modify-user/{userid}/", response_class=HTMLResponse)
async def modify_user(request: Request, userid: int, user_id: int = Depends(get_current_user)):
    conn = get_db_connection()
    user = conn.execute('SELECT * FROM users WHERE userid = ?', (userid,)).fetchone()
    conn.close()
    if user:
        return templates.TemplateResponse("modify_user.html", {"request": request, "user": user})
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

@app.post("/modify-user/{userid}/")
async def modify_user_post(userid: int, username: str = Form(...), password: str = Form(...), user_id: int = Depends(get_current_user)):
    conn = get_db_connection()
    conn.execute('UPDATE users SET username = ?, password = ? WHERE userid = ?', (username, password, userid))
    conn.commit()
    conn.close()
    return RedirectResponse(url="/users/", status_code=303)

@app.get("/delete-user/{userid}/")
async def delete_user(userid: int, user_id: int = Depends(get_current_user)):
    conn = get_db_connection()
    conn.execute('DELETE FROM users WHERE userid = ?', (userid,))
    conn.commit()
    conn.close()
    return RedirectResponse(url="/users/", status_code=303)

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

@app.get("/dashboard/", response_class=HTMLResponse)
async def dashboard(request: Request, user_id: int = Depends(get_current_user)):
    conn = get_db_connection()
    user = conn.execute('SELECT username FROM users WHERE userid = ?', (user_id,)).fetchone()
    conn.close()

    if user:
        return templates.TemplateResponse("dashboard.html", {"request": request, "username": user['username']})
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

@app.get("/logout/")
async def logout(request: Request):
    request.session.pop('user_id', None)  # Remove the user ID from the session
    return RedirectResponse(url="/login/", status_code=303)

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
