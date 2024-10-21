import os

import git

# Path to your Git repository (local path)
git_repo_path = os.getenv("GIT_REPO_PATH", "default_git_repo_path")

# Initialize the Git repository
repo = git.Repo(git_repo_path)

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

# Function to commit specific template changes
def commit_template_changes(template_name: str, message: str):
    """Commits changes to a specific template file.

    Args:
        template_name (str): The name of the template file to commit.
        message (str): The commit message.

    """
    try:
        repo.index.add([f"templates/{template_name}"])  # Adjust the path accordingly
        repo.index.commit(message)
        push_changes()  # Push changes to remote
    except Exception as e:
        print(f"Error committing template changes: {e}")
