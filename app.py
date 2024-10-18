
import logging
import os

from fastapi import FastAPI, Form, HTTPException, Request, status
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates

app = FastAPI()
templates = Jinja2Templates(directory="templates")

GIT_REPO_PATH = "/path/to/git/repo"
TEMPLATE_DIR = "/path/to/templates"
BLOG_CONTENT_PATH = "/path/to/blog/content"

# --- Common Helper Functions ---

def get_logged_in_user(request: Request):
    # Placeholder for actual user retrieval logic
    return request.session.get('user')

def handle_login_redirect(request: Request):
    user = get_logged_in_user(request)
    if not user:
        return RedirectResponse(url="/login/", status_code=303)
    return user

def handle_file_operation(func, *args):
    try:
        func(*args)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

# --- Git-related Routes ---

@app.get("/admin/blog/git/files/")
async def list_git_files(request: Request):
    user = handle_login_redirect(request)
    if isinstance(user, RedirectResponse):
        return user

    files = list_files()
    return templates.TemplateResponse("git_files.html", {"request": request, "files": files, "user": user})

@app.post("/admin/blog/git/add-file/")
async def add_git_file(request: Request, file_path: str = Form(...)):
    user = handle_login_redirect(request)
    if isinstance(user, RedirectResponse):
        return user

    handle_file_operation(add_file, file_path)
    return RedirectResponse(url="/admin/blog/git/files/", status_code=303)

@app.post("/admin/blog/git/remove-file/")
async def remove_git_file(request: Request, file_path: str = Form(...)):
    user = handle_login_redirect(request)
    if isinstance(user, RedirectResponse):
        return user

    handle_file_operation(remove_file, file_path)
    return RedirectResponse(url="/admin/blog/git/files/", status_code=303)

# --- Template Management Routes ---

def list_html_templates():
    template_dir = TEMPLATE_DIR
    try:
        templates = [f for f in os.listdir(template_dir) if f.endswith('.html')]
    except (FileNotFoundError, PermissionError) as e:
        logging.error(f"Error accessing template directory: {e}")
        return []
    return templates

def list_markdown_files(page: int = 1, limit: int = 20, section: str = None):
    markdown_dir = BLOG_CONTENT_PATH
    markdown_files = []

    for root, _, files in os.walk(markdown_dir):
        for f in files:
            if f.endswith('.md') and f != '_index.md':
                full_path = os.path.join(root, f)
                markdown_files.append(full_path)

    return markdown_files[(page - 1) * limit: page * limit]

# Other template and post-related routes can follow here.
# Example:

@app.get("/new-post-added/", response_class=HTMLResponse)
async def new_post_added(
    request: Request,
    template_name: str,
    category: str,
    subcategory: str = None
):
    user = handle_login_redirect(request)
    if isinstance(user, RedirectResponse):
        return user

    return templates.TemplateResponse("new_post_added.html", {
        "request": request,
        "template_name": template_name,
        "category": category,
        "subcategory": subcategory or "none",
    })

# Define other routes below following the same structure.
