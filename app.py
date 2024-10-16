import logging
import os
import sqlite3

from dotenv import load_dotenv
from fastapi import FastAPI, Form, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from passlib.hash import pbkdf2_sha256
from starlette.middleware.sessions import SessionMiddleware
from starlette.responses import RedirectResponse

from git_helper import add_file, list_files, remove_file

# Load environment variables
load_dotenv()

# Initialize FastAPI app
app = FastAPI()

# Configure session middleware
secret_key = os.getenv("SECRET_KEY", "default_secret_key")
app.add_middleware(SessionMiddleware, secret_key=secret_key)

# Configure your Git repository (local path)
GIT_REPO_PATH = os.getenv("GIT_REPO_PATH")
template_dir = os.path.join(GIT_REPO_PATH, "content/blog/")
BLOG_CONTENT_PATH = os.path.join(GIT_REPO_PATH, "content", "blog")

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
    with get_db_connection() as conn:
        user = conn.execute('SELECT * FROM users WHERE userid = ?', (user_id,)).fetchone()
    return user

# Helper function to hash the password
def hash_password(password: str) -> str:
    return pbkdf2_sha256.hash(password)

def verify_password(password: str, hashed_password: str) -> bool:
    return pbkdf2_sha256.verify(password, hashed_password)

# Routes

@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    user = get_logged_in_user(request)
    return templates.TemplateResponse("index.html", {"request": request, "user": user})

@app.get("/dashboard/", response_class=HTMLResponse)
async def dashboard(request: Request):
    user = get_logged_in_user(request)
    if not user:
        return RedirectResponse(url="/login/", status_code=303)
    return templates.TemplateResponse("dashboard.html", {"request": request, "user": user})

@app.get("/login/", response_class=HTMLResponse)
async def login(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@app.post("/login/")
async def login_post(request: Request, username: str = Form(...), password: str = Form(...)):
    with get_db_connection() as conn:
        user = conn.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()

    if user and verify_password(password, user['password']):
        request.session['user_id'] = user['userid']
        return RedirectResponse(url="/dashboard/", status_code=303)

    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

@app.get("/logout/")
async def logout(request: Request):
    request.session.pop('user_id', None)
    return RedirectResponse(url="/login/", status_code=303)

# User management routes

@app.get("/users/", response_class=HTMLResponse)
async def get_users(request: Request):
    user = get_logged_in_user(request)
    if not user:
        return RedirectResponse(url="/login/", status_code=303)

    with get_db_connection() as conn:
        users = conn.execute('SELECT * FROM users').fetchall()
    return templates.TemplateResponse("users.html", {"request": request, "users": users, "user": user})

@app.get("/add-user/", response_class=HTMLResponse)
async def add_user_form(request: Request):
    user = get_logged_in_user(request)
    if not user:
        return RedirectResponse(url="/login/", status_code=303)
    return templates.TemplateResponse("add_user.html", {"request": request, "user": user})

@app.post("/add-user/")
async def add_user(request: Request, username: str = Form(...), password: str = Form(...)):
    user = get_logged_in_user(request)
    if not user:
        return RedirectResponse(url="/login/", status_code=303)

    hashed_password = hash_password(password)

    with get_db_connection() as conn:
        try:
            conn.execute('INSERT INTO users (username, password) VALUES (?, ?)', (username, hashed_password))
            conn.commit()
        except sqlite3.IntegrityError:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="User already exists.")
    return RedirectResponse(url="/users/", status_code=303)

@app.get("/modify-user/{userid}/", response_class=HTMLResponse)
async def modify_user(request: Request, userid: int):
    user = get_logged_in_user(request)
    if not user:
        return RedirectResponse(url="/login/", status_code=303)

    with get_db_connection() as conn:
        target_user = conn.execute('SELECT * FROM users WHERE userid = ?', (userid,)).fetchone()
    if target_user:
        return templates.TemplateResponse("modify_user.html", {"request": request, "user": user, "target_user": target_user})
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

@app.post("/modify-user/{userid}/")
async def modify_user_post(request: Request, userid: int, username: str = Form(...), password: str = Form(...)):
    user = get_logged_in_user(request)
    if not user:
        return RedirectResponse(url="/login/", status_code=303)

    hashed_password = hash_password(password)

    with get_db_connection() as conn:
        conn.execute('UPDATE users SET username = ?, password = ? WHERE userid = ?', (username, hashed_password, userid))
        conn.commit()
    return RedirectResponse(url="/users/", status_code=303)

@app.get("/delete-user/{userid}/")
async def delete_user(request: Request, userid: int):
    user = get_logged_in_user(request)
    if not user:
        return RedirectResponse(url="/login/", status_code=303)

    with get_db_connection() as conn:
        conn.execute('DELETE FROM users WHERE userid = ?', (userid,))
        conn.commit()
    return RedirectResponse(url="/users/", status_code=303)

# Git file management routes

@app.get("/admin/blog/git/files/", response_class=HTMLResponse)
async def list_git_files(request: Request):
    user = get_logged_in_user(request)
    if not user:
        return RedirectResponse(url="/login/", status_code=303)

    files = list_files()
    return templates.TemplateResponse("git_files.html", {"request": request, "files": files, "user": user})

@app.post("/admin/blog/git/add-file/")
async def add_git_file(request: Request, file_path: str = Form(...)):
    user = get_logged_in_user(request)
    if not user:
        return RedirectResponse(url="/login/", status_code=303)

    try:
        add_file(file_path)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
    return RedirectResponse(url="/admin/blog/git/files/", status_code=303)

@app.post("/admin/blog/git/remove-file/")
async def remove_git_file(request: Request, file_path: str = Form(...)):
    user = get_logged_in_user(request)
    if not user:
        return RedirectResponse(url="/login/", status_code=303)

    try:
        remove_file(file_path)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
    return RedirectResponse(url="/admin/blog/git/files/", status_code=303)

# Template management routes


def list_html_templates():
    template_dir = os.path.join(GIT_REPO_PATH, 'templates')
    try:
        templates = [f for f in os.listdir(template_dir) if f.endswith('.html')]
    except FileNotFoundError:
        logging.error(f"Template directory not found: {template_dir}")
        return []
    except PermissionError:
        logging.error(f"Permission denied accessing: {template_dir}")
        return []
    return templates

@app.get("/templates/", response_class=HTMLResponse)
async def get_templates(request: Request):
    user = get_logged_in_user(request)
    if not user:
        return RedirectResponse(url="/login/", status_code=303)

    templates_list = list_html_templates()
    return templates.TemplateResponse("templates_list.html", {"request": request, "templates": templates_list, "user": user})

@app.get("/templates/new/", response_class=HTMLResponse)
async def new_template(request: Request):
    user = get_logged_in_user(request)
    if not user:
        return RedirectResponse(url="/login/", status_code=303)

    return templates.TemplateResponse("new_template.html", {"request": request, "user": user})


#Adding New Blog Post.
@app.post("/templates/new/")
async def create_template(
    template_name: str = Form(...),
    category: str = Form(...),
    subcategory: str = Form(...),
    description: str = Form(...),
    keywords: str = Form(...),
    date: str = Form(...),
    draft: bool = Form(...),
    og_title: str = Form(...),
    og_description: str = Form(...),
    og_image: str = Form(...),
    og_url: str = Form(...),
    og_type: str = Form(...),
    author: str = Form(...),
    viewport: str = Form(...),
    json_ld_name: str = Form(...),
    json_ld_description: str = Form(...),
    json_ld_url: str = Form(...),
    content: str = Form(...)
):
    # Validate inputs early
    if not template_name.isalnum():
        raise HTTPException(status_code=400, detail="Template name must be alphanumeric.")
    if not category or not template_name:
        raise HTTPException(status_code=400, detail="Category and template name cannot be empty.")

    # Create the folder structure based on the category and subcategory
    folder_path = os.path.join(BLOG_CONTENT_PATH, category)
    if subcategory and subcategory.lower() != "none":
        folder_path = os.path.join(folder_path, subcategory)

    # Safely create directories
    try:
        os.makedirs(folder_path, exist_ok=True)
    except OSError as e:
        logging.error(f"Error creating directory: {folder_path}, {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to create the directory for the template.")

    # Prepare the file name for the markdown file
    file_name = f"{template_name}.md"  # Use template_name for file name
    file_path = os.path.join(folder_path, file_name)

    # Check if the file already exists
    if os.path.exists(file_path):
        raise HTTPException(status_code=400, detail="A template with this name already exists.")

    # Format the front matter for the markdown file
    front_matter = f"""
+++
title = "{template_name}"  # Use template_name in front matter
description = "{description}"
keywords = "{keywords}"
date = "{date}"
draft = {str(draft).lower()}
og_title = "{og_title}"
og_description = "{og_description}"
og_image = "{og_image}"
og_url = "{og_url}"
og_type = "{og_type}"
author = "{author}"
viewport = "{viewport}"
json_ld = {{
    "name": "{json_ld_name}",
    "description": "{json_ld_description}",
    "url": "{json_ld_url}"
}}
+++
    """

    # Combine front matter and the content provided in the form
    full_content = front_matter.strip() + "\n\n" + content.strip()

    # Write the markdown content to the file
    try:
        with open(file_path, "w") as f:
            f.write(full_content)
    except OSError as e:
        logging.error(f"Error writing to file: {file_path}, {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to write the template file.")

    # Use GitPython to add, commit, and push changes to the GitHub repository
    try:
        repo = Repo(GIT_REPO_PATH)
        repo.git.add(file_path)
        repo.index.commit(f"Add new template: {template_name}")  # Use template_name in commit message
        origin = repo.remote(name="origin")
        origin.push()
    except Exception as e:
        logging.error(f"Git operation failed: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to commit and push the changes to the repository.")

    # Redirect back to the template list page after successful creation
    return RedirectResponse(url="/templates/", status_code=303)

@app.get("/templates/edit/{template_name}", response_class=HTMLResponse)
async def edit_template(request: Request, template_name: str):
    user = get_logged_in_user(request)
    if not user:
        return RedirectResponse(url="/login/", status_code=303)

    template_path = os.path.join(template_dir, template_name)
    if os.path.exists(template_path):
        with open(template_path) as file:
            content = file.read()
        return templates.TemplateResponse("edit_template.html", {"request": request, "user": user, "template_name": template_name, "content": content})

    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Template not found.")

@app.post("/templates/edit/{template_name}")
async def update_template(request: Request, template_name: str, content: str = Form(...)):
    user = get_logged_in_user(request)
    if not user:
        return RedirectResponse(url="/login/", status_code=303)

    template_path = os.path.join(template_dir, template_name)
    if os.path.exists(template_path):
        with open(template_path, 'w') as file:
            file.write(content)
        return RedirectResponse(url="/templates/", status_code=303)

    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Template not found.")

@app.get("/templates/delete/{template_name}")
async def delete_template(request: Request, template_name: str):
    user = get_logged_in_user(request)
    if not user:
        return RedirectResponse(url="/login/", status_code=303)

    template_path = os.path.join(template_dir, template_name)
    if os.path.exists(template_path):
        os.remove(template_path)
        return RedirectResponse(url="/templates/", status_code=303)

    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Template not found.")

# Run the app
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
