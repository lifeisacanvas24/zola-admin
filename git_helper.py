# git_helper.py
import os

import git

# Path to your Git repository (local path)
REPO_PATH = os.getenv('GIT_REPO_PATH', '/Users/aravindkumar/Library/Mobile Documents/com~apple~CloudDocs/projects/git-repos/rust/lifeisacanvas24.github.io')  # Change this to your actual repository path

# Initialize the Git repository
repo = git.Repo(REPO_PATH)

def get_repo():
    """Returns the initialized Git repository."""
    return repo

def add_file(file_path):
    """Adds a file to the repository and commits the change.

    Args:
        file_path (str): The path to the file to add.

    """
    try:
        repo.index.add([file_path])
        repo.index.commit(f'Add {file_path}')
        push_changes()  # Push changes after committing
    except Exception as e:
        print(f"Error adding file: {e}")

def remove_file(file_path):
    """Removes a file from the repository and commits the change.

    Args:
        file_path (str): The path to the file to remove.

    """
    try:
        repo.index.remove([file_path])
        repo.index.commit(f'Remove {file_path}')
        push_changes()  # Push changes after committing
    except Exception as e:
        print(f"Error removing file: {e}")

def push_changes():
    """Pushes changes to the remote repository."""
    try:
        origin = repo.remote(name='origin')
        origin.push()  # Push to the remote repository
    except Exception as e:
        print(f"Error pushing changes: {e}")

def list_files():
    """Lists all files in the repository.

    Returns:
        list: A list of file paths in the repository.

    """
    return [item.path for item in repo.tree().traverse()]

def commit_changes(message: str):
    """Commits all changes in the repository with a provided message and pushes the changes.

    Args:
        message (str): The commit message.

    """
    try:
        repo.git.add(A=True)  # Stage all changes
        repo.index.commit(message)  # Commit with the provided message
        push_changes()  # Push changes to remote
    except Exception as e:
        print(f"Error committing changes: {e}")
