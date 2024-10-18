import logging
import os
import sqlite3
from datetime import datetime  # <-- Add this import
from typing import Optional  # Add this import
from urllib.parse import quote

from dotenv import load_dotenv
from fastapi import FastAPI, Form, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from git import Repo
from passlib.hash import pbkdf2_sha256
from starlette.middleware.sessions import SessionMiddleware
from starlette.responses import RedirectResponse

from git_helper import add_file, list_files, remove_file

# logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

logging.basicConfig(level=logging.INFO)

# Set the environment variable for SSH command
os.environ['GIT_SSH_COMMAND'] = 'ssh -i ~/.ssh/git-zola-cms -o IdentitiesOnly=yes'

# Load environment variables
load_dotenv()

# Initialize FastAPI app
app = FastAPI()

# Configure session middleware
secret_key = os.getenv("SECRET_KEY", "default_secret_key")
app.add_middleware(SessionMiddleware, secret_key=secret_key)

# Configure your Git repository (local path)
GIT_REPO_PATH = os.getenv("GIT_REPO_PATH")
TEMPLATE_DIR = os.path.join(GIT_REPO_PATH, "templates")
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
# def get_logged_in_user(request: Request):
    # user_id = request.session.get('user_id')
    # if not user_id:
        # return None
    # with get_db_connection() as conn:
        # user = conn.execute('SELECT * FROM users WHERE userid = ?', (user_id,)).fetchone()
    # return user

# Helper function to get the logged-in user
def get_logged_in_user(request: Request):
    user_id = get_current_user_id_from_session(request)

    if user_id:
        with get_db_connection() as conn:
            # Remove 'role' from the selection
            user = conn.execute('SELECT userid, username FROM users WHERE userid = ?', (user_id,)).fetchone()
            return user  # Now this only returns userid and username
    return None

def get_current_user_id_from_session(request: Request):
    return request.session.get("user_id")

# Helper function to hash the password
def hash_password(password: str) -> str:
    return pbkdf2_sha256.hash(password)

def verify_password(password: str, hashed_password: str) -> bool:
    return pbkdf2_sha256.verify(password, hashed_password)

# Define the custom filter for URL encoding
def url_encode(s):
    return quote(s)

# Add the filter to the Jinja2 environment
templates.env.filters["url_encode"] = url_encode

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
async def login(request: Request, username: str = Form(...), password: str = Form(...)):
    with get_db_connection() as conn:
        user = conn.execute('SELECT userid, username, password FROM users WHERE username = ?', (username,)).fetchone()

    if user and verify_password(password, user["password"]):  # Use your verify function
        request.session["user_id"] = user["userid"]  # Store user ID in session
        return RedirectResponse(url="/dashboard/", status_code=303)

    raise HTTPException(status_code=401, detail="Invalid credentials")

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

    hashed_password = hash_password(password)  # Use your hash function

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
    template_dir = TEMPLATE_DIR
    try:
        templates = [f for f in os.listdir(template_dir) if f.endswith('.html')]
    except FileNotFoundError:
        logging.error(f"Template directory not found: {template_dir}")
        return []
    except PermissionError:
        logging.error(f"Permission denied accessing: {template_dir}")
        return []
    return templates

def list_markdown_files(page: int = 1, limit: int = 20, section: str = None):
    markdown_dir = BLOG_CONTENT_PATH
    markdown_files = []

    try:
        for root, _, files in os.walk(markdown_dir):
            for f in files:
                if f.endswith('.md') and f != '_index.md':
                    full_path = os.path.join(root, f)

                    # Create the display path based on the relative directory structure
                    relative_root = os.path.relpath(root, markdown_dir)
                    if relative_root == ".":
                        display_path = f"Content -> {f}"
                    elif "blog" in relative_root.lower():
                        display_path = f"Content -> Blog -> {relative_root.replace(os.sep, ' -> ')} -> {f}"
                    else:
                        display_path = f"Content -> {relative_root.replace(os.sep, ' -> ')} -> {f}"

                    markdown_files.append(display_path)

        # Optionally filter by section
        if section:
            markdown_files = [f for f in markdown_files if section in f]

        # Implement pagination
        start = (page - 1) * limit
        end = start + limit
        return markdown_files[start:end], len(markdown_files)  # Return both the files and total count

    except FileNotFoundError:
        logging.error(f"Markdown directory not found: {markdown_dir}")
        return [], 0
    except PermissionError:
        logging.error(f"Permission denied accessing: {markdown_dir}")
        return [], 0


def parse_front_matter(markdown_content):
    # Simple parser for front matter (adjust as needed)
    if markdown_content.startswith('+++'):
        parts = markdown_content.split('+++')[1:]
        front_matter = parts[0].strip()  # Extract front matter
        content = ''.join(parts[1:]).strip()  # Remaining content
        return front_matter, content
    return "", markdown_content  # No front matter found

@app.get("/markdown/", response_class=HTMLResponse)
async def get_markdown_files(request: Request, page: int = 1, section: str = None):
    user = get_logged_in_user(request)

    # Redirect to login if the user is not authenticated
    if not user:
        return RedirectResponse(url="/login/", status_code=303)

    # Get the list of Markdown files and the total number of files
    markdown_files_list, total_files = list_markdown_files(page=page, limit=20, section=section)

    # Calculate the total number of pages
    total_pages = (total_files + 19) // 20  # Round up for total pages

    # Render the template with the necessary context
    return templates.TemplateResponse("markdown_list.html", {
        "request": request,
        "markdown_files": markdown_files_list,
        "user": user,
        "page": page,
        "total_pages": total_pages,
        "section": section  # Pass the current section for filtering
    })

@app.get("/markdown/edit/{category}/{subcategory}/{file_name}", response_class=HTMLResponse)
async def edit_markdown(request: Request, category: str, subcategory: str, file_name: str):
        user = get_logged_in_user(request)
        if not user:
            return RedirectResponse(url="/login/", status_code=303)

        # Construct the full path to the markdown file
        markdown_path = os.path.join(BLOG_CONTENT_PATH, category, subcategory, file_name) if subcategory else os.path.join(BLOG_CONTENT_PATH, category, file_name)

        if not os.path.exists(markdown_path):
            raise HTTPException(status_code=404, detail="Markdown file not found")

        with open(markdown_path) as f:
            markdown_content = f.read()

        # Assume you have a function to extract front matter from the markdown content
        front_matter, content = parse_front_matter(markdown_content)

        return templates.TemplateResponse("edit_markdown.html", {
            "request": request,
            "file_name": file_name,
            "markdown_content": content,
            "front_matter": front_matter,
            "user": user,
            "category": category,
            "subcategory": subcategory,
        })

@app.post("/markdown/edit/{category}/{subcategory}/{file_name}")
async def edit_markdown_post(
        request: Request,
        category: str,
        subcategory: str,
        file_name: str,
        title: str = Form(...),
        description: str = Form(...),
        date: str = Form(...),
        draft: bool = Form(...),
        og_image: str = Form(...),
        keywords: str = Form(...),
        content: str = Form(...),
    ):
        user = get_logged_in_user(request)
        if not user:
            return RedirectResponse(url="/login/", status_code=303)

        # Construct the full path to the markdown file
        markdown_path = os.path.join(BLOG_CONTENT_PATH, category, subcategory, file_name) if subcategory else os.path.join(BLOG_CONTENT_PATH, category, file_name)

        if not os.path.exists(markdown_path):
            raise HTTPException(status_code=404, detail="Markdown file not found")

        # Generate the updated front matter
        front_matter = f"""+++
    title = "{title}"
    description = "{description}"
    date = "{date}"
    draft = {str(draft).lower()}
    updated = "{datetime.now().isoformat()}"
    reading_time = "N/A"
    social_image = "{og_image}"
    tags = [{', '.join([f'"{tag.strip()}"' for tag in keywords.split(',')])}]
    +++"""

        # Combine front matter with content
        template_content = front_matter + "\n" + content

        # Write the updated content to the file
        try:
            with open(markdown_path, 'w') as f:
                f.write(template_content)
        except OSError as e:
            logging.error(f"Error writing to file: {markdown_path}, {str(e)}")
            raise HTTPException(status_code=500, detail="Failed to update the Markdown file.")

        # Commit and push changes to Git
        try:
            repo = Repo(GIT_REPO_PATH)
            repo.git.add(markdown_path)
            repo.index.commit(f"Edit markdown file: {file_name}")
            origin = repo.remote(name="origin")
            origin.push()
        except Exception as e:
            logging.error(f"Git operation failed: {str(e)}")
            raise HTTPException(status_code=500, detail="Failed to commit and push the changes to the repository.")

        return RedirectResponse(url="/markdown/", status_code=303)

@app.post("/markdown/delete/{full_path:path}")
async def delete_markdown_file(request: Request, full_path: str):
    user = get_logged_in_user(request)
    if not user:
        return RedirectResponse(url="/login/", status_code=303)

    # Log the incoming parameters
    logging.info(f"Delete request for path: {full_path}")

    # Split the full path into parts
    path_parts = full_path.split('/')
    category = path_parts[0]
    file_name = path_parts[-1]
    subcategory = '/'.join(path_parts[1:-1]) if len(path_parts) > 2 else None

    logging.info(f"Parsed path - category: {category}, subcategory: {subcategory}, file_name: {file_name}")

    # Construct the file path
    file_path = os.path.join(BLOG_CONTENT_PATH, full_path)
    logging.info(f"Constructed file path: {file_path}")

    if not os.path.exists(file_path):
        logging.error(f"File not found: {file_path}")
        raise HTTPException(status_code=404, detail="File not found")

    # Pull the latest changes from the remote repository
    try:
        repo = Repo(GIT_REPO_PATH)
        repo.git.pull('origin', 'master')  # or 'main', depending on your branch
        logging.info("Successfully pulled the latest changes from the remote repository.")
    except Exception as e:
        logging.error(f"Git pull failed: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to pull the latest changes from the repository.")

    # Attempt to delete the file
    try:
        os.remove(file_path)
        logging.info(f"File successfully deleted: {file_path}")
    except OSError as e:
        logging.error(f"Error deleting file: {file_path}, {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to delete the file.")

    # Commit and push the deletion to Git
    try:
        repo.git.add(file_path)  # Stage the deletion
        repo.index.commit(f"Delete file: {full_path}")  # Commit the deletion
        push_result = repo.git.push('origin', 'master', '--verbose')  # Push changes to the remote

        logging.info(f"Git operations successful for deleting: {full_path}")

    except Exception as e:
        logging.error(f"Git operation failed: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to commit and push the deletion to the repository.")

    return RedirectResponse(url="/markdown/", status_code=303)

@app.get("/templates/", response_class=HTMLResponse)
async def templates_index(request: Request):
    user = get_logged_in_user(request)
    if not user:
        return RedirectResponse(url="/login/", status_code=303)

    templates_list = list_html_templates()
    return templates.TemplateResponse("templates.html", {"request": request, "templates": templates_list, "user": user})

@app.get("/templates/new/", response_class=HTMLResponse)
async def new_template(request: Request):
    user = get_logged_in_user(request)
    if not user:
        return RedirectResponse(url="/login/", status_code=303)

    return templates.TemplateResponse("new_template.html", {"request": request, "user": user})

@app.post("/templates/new/")
async def new_template_post(request: Request, template_name: str = Form(...), content: str = Form(...)):
    user = get_logged_in_user(request)
    if not user:
        return RedirectResponse(url="/login/", status_code=303)

    template_path = os.path.join(TEMPLATE_DIR, f"{template_name}.html")

    try:
        with open(template_path, 'w') as f:
            f.write(content)
    except OSError as e:
        logging.error(f"Error writing to file: {template_path}, {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to create the template file.")

    # Commit the new template to Git
    try:
        repo = Repo(GIT_REPO_PATH)
        repo.git.add(template_path)
        repo.index.commit(f"Add new template: {template_name}")
        origin = repo.remote(name="origin")
        origin.push()
    except Exception as e:
        logging.error(f"Git operation failed: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to commit and push the changes to the repository.")

    return RedirectResponse(url="/templates/", status_code=303)

@app.get("/templates/edit/{template_name}", response_class=HTMLResponse)
async def edit_template(request: Request, template_name: str):
    user = get_logged_in_user(request)
    if not user:
        return RedirectResponse(url="/login/", status_code=303)

    template_path = os.path.join(TEMPLATE_DIR, f"{template_name}.html")
    if not os.path.exists(template_path):
        raise HTTPException(status_code=404, detail="Template not found")

    with open(template_path) as f:
        template_content = f.read()

    return templates.TemplateResponse("edit_template.html", {
        "request": request,
        "template_name": template_name,
        "template_content": template_content,
        "user": user
    })

@app.post("/templates/edit/{template_name}")
async def edit_template_post(request: Request, template_name: str, content: str = Form(...)):
    user = get_logged_in_user(request)
    if not user:
        return RedirectResponse(url="/login/", status_code=303)

    template_path = os.path.join(TEMPLATE_DIR, f"{template_name}.html")
    if not os.path.exists(template_path):
        raise HTTPException(status_code=404, detail="Template not found")

    try:
        with open(template_path, 'w') as f:
            f.write(content)
    except OSError as e:
        logging.error(f"Error writing to file: {template_path}, {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to update the template file.")

    try:
        repo = Repo(GIT_REPO_PATH)
        repo.git.add(template_path)
        repo.index.commit(f"Edit template: {template_name}")
        origin = repo.remote(name="origin")
        origin.push()
    except Exception as e:
        logging.error(f"Git operation failed: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to commit and push the changes to the repository.")

    return RedirectResponse(url="/templates/", status_code=303)

@app.get("/templates/delete/{template_name}")
async def delete_template(request: Request, template_name: str):
    user = get_logged_in_user(request)
    if not user:
        return RedirectResponse(url="/login/", status_code=303)

    template_path = os.path.join(TEMPLATE_DIR, f"{template_name}.html")
    if not os.path.exists(template_path):
        raise HTTPException(status_code=404, detail="Template not found")

    try:
        os.remove(template_path)
    except OSError as e:
        logging.error(f"Error deleting file: {template_path}, {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to delete the template file.")

    try:
        repo = Repo(GIT_REPO_PATH)
        repo.git.rm(template_path)
        repo.index.commit(f"Delete template: {template_name}")
        origin = repo.remote(name="origin")
        origin.push()
    except Exception as e:
        logging.error(f"Git operation failed: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to commit and push the changes to the repository.")

    return RedirectResponse(url="/templates/", status_code=303)

@app.get("/add-new-post/", response_class=HTMLResponse)
async def new_post(request: Request):
    user = get_logged_in_user(request)
    if not user:
        return RedirectResponse(url="/login/", status_code=303)

    return templates.TemplateResponse("new_post.html", {"request": request, "user": user})

@app.post("/add-new-post/")
async def add_new_post(
    request: Request,
    template_name: str = Form(...),
    category: str = Form(...),
    subcategory: str = Form(None),  # Subcategory is optional
    description: str = Form(...),
    keywords: str = Form(...),
    date: str = Form(None),  # Optional, auto-generate if not provided
    draft: bool = Form(False),  # Draft should not be mandatory
    og_title: str = Form(None),  # Optional OG metadata fields
    og_description: str = Form(None),
    og_image: str = Form(None),
    og_url: str = Form(None),
    og_type: str = Form(None),
    author: str = Form(...),
    viewport: str = Form(None),
    json_ld_name: str = Form(None),
    json_ld_description: str = Form(None),
    json_ld_url: str = Form(None),
    content: str = Form(...),
):
    subcategory_path = subcategory if subcategory else ""

    # Handling date - default to now if not provided
    post_date = date if date else datetime.now().isoformat()

    # Prepare front matter
    front_matter = f"""+++
title = "{template_name}"
description = "{description}"
date = "{post_date}"
draft = {str(draft).lower()}
updated = "{datetime.now().isoformat()}"
reading_time = "N/A"
social_image = "{og_image or ''}"
tags = [{', '.join([f'"{tag.strip()}"' for tag in keywords.split(',')])}]
categories = ["{category}", "{subcategory_path}"]
+++"""

    # Handle Open Graph metadata (Optional)
    if og_title or og_description or og_image or og_url or og_type:
        front_matter += f"""
[open_graph]
title = "{og_title or ''}"
description = "{og_description or ''}"
image = "{og_image or ''}"
url = "{og_url or ''}"
type = "{og_type or ''}"
"""

    # Prepare JSON-LD data (Optional)
    json_ld_metadata = ""
    if json_ld_name or json_ld_description or json_ld_url:
        json_ld_metadata = f"""
<script type="application/ld+json">
{{
  "@context": "https://schema.org",
  "@type": "BlogPosting",
  "name": "{json_ld_name or ''}",
  "description": "{json_ld_description or ''}",
  "url": "{json_ld_url or ''}",
  "author": "{author}",
  "datePublished": "{post_date}"
}}
</script>
"""

    # Generate file path
    template_file_name = f"{template_name.replace(' ', '-').lower()}.md"
    template_path = os.path.join(BLOG_CONTENT_PATH, category, subcategory_path, template_file_name)

    # Write content to file (front matter + content + JSON-LD)
    try:
        os.makedirs(os.path.dirname(template_path), exist_ok=True)
        with open(template_path, 'w') as f:
            f.write(front_matter + "\n" + content + "\n" + json_ld_metadata)
    except OSError as e:
        logging.error(f"Error writing to file: {template_path}, {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to create the template file.")

    # Handle Git operations
    try:
        repo = Repo(GIT_REPO_PATH)
        repo.git.add(template_path)
        repo.index.commit(f"Add new post: {template_name}")
        origin = repo.remote(name="origin")
        origin.push()
    except Exception as e:
        logging.error(f"Git operation failed: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to commit and push the changes to the repository.")

    return RedirectResponse(
    url=f"/new-post-added/?template_name={quote(template_name)}&category={quote(category)}&subcategory={quote(subcategory)}",
    status_code=302)

@app.get("/new-post-added/", response_class=HTMLResponse)
async def new_post_added(
    request: Request,
    template_name: str,
    category: str,
    subcategory: Optional[str] = None
):
    user = get_logged_in_user(request)
    if not user:
        return RedirectResponse(url="/login/", status_code=303)

    return templates.TemplateResponse("new_post_added.html", {
        "request": request,
        "template_name": template_name,
        "category": category,
        "subcategory": subcategory or "none",  # Handle if subcategory is None
    })
