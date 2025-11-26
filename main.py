from mcp.server.fastmcp import FastMCP
import os
import subprocess
import logging
import sys

# Configure logging to write to a file
logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('mcp_server.log'),  # Write to file
        logging.StreamHandler(sys.stderr)        # Also write to stderr
    ]
)

mcp = FastMCP("filesystem-explorer")
destination_path = os.getcwd()+"/storage/"
uploaded_files_path = "/home/piyush/.local/lib/python3.12/site-packages/open_webui/data/uploads/"

@mcp.tool()
def clone_github_repo(url: str) -> str:
    """
    Clone a GitHub repository. 
    Args:
        url (str): The URL of the GitHub repository to clone.
    Returns:
        str: The path to the cloned repository or an error message.
    """
    try:
        # Extract the repository name from the URL
        repo_name = url.rstrip('/').split('/')[-1]
        if repo_name.endswith('.git'):
            repo_name = repo_name[:-4]
            
        repo_destination = os.path.join(destination_path, repo_name)

        # Create the destination directory if it doesn't exist
        if not os.path.exists(destination_path):
            os.makedirs(destination_path)
            logging.info(f"Created directory: {destination_path}")

        # Construct the git clone command
        command = ["git", "clone", str(url), repo_destination]

        # Execute the command
        subprocess.run(command, check=True, capture_output=True, text=True)
        return f"Repository '{url}' cloned successfully to '{repo_destination}'."
    except subprocess.CalledProcessError as e:
        return f"Error cloning repository: {e.stderr}"
    except Exception as e:
        return f"An unexpected error occurred: {str(e)}"


def build_files(directory: str, max_depth: int = 0) -> str:
    """
    Build a string representation of files and directories.
    Args:
        directory: The root directory to list
        max_depth: Maximum depth to traverse (0 = current dir only, 1 = one level deep, etc.)
    """
    output = ""
    
    def _list_dir(path: str, current_depth: int = 0):
        nonlocal output
        try:
            items = os.listdir(path)
            dirs = [item for item in items if os.path.isdir(os.path.join(path, item)) and "git" not in item]
            files = [item for item in items if os.path.isfile(os.path.join(path, item))]
            
            output += f"Directory: {path}\n"
            if dirs:
                output += f"  Subdirectories: {', '.join(dirs)}\n"
            if files:
                output += f"  Files: {', '.join(files)}\n"
            output += "\n"
            
            # Recursively list subdirectories if we haven't reached max depth
            if current_depth < max_depth:
                for d in dirs:
                    _list_dir(os.path.join(path, d), current_depth + 1)
        except PermissionError:
            output += f"Directory: {path}\n  Error: Permission denied\n\n"
    
    _list_dir(directory)
    return output

@mcp.tool()
def list_files(directory: str) -> str:
    """
    List the files in a directory. 
    Args:
        directory (str): The directory to list files from. If the directory is not specified, the current directory is used. That is, directory = os.getcwd()
        Default: .
    Returns:
        str: The list of files in the directory.
    """
    try:
        # Default to storage folder when directory is empty or "."
        if directory == "." or directory == "":
            output = "--- Storage Folder ---\n"
            output += build_files(destination_path, max_depth=100)
            
            if os.path.exists(uploaded_files_path):
                output += "\n--- Uploaded Files ---\n"
                output += build_files(uploaded_files_path, max_depth=100)
        else:
            # If a specific directory is requested, list that
            output = build_files(directory, max_depth=100)
        logging.info(f"output: {output}")
        logging.info(f"Listed files successfully")
        return output
    except FileNotFoundError:
        return f"Error: Directory '{directory}' not found."
    except PermissionError:
        return f"Error: Permission denied for directory '{directory}'."
    except Exception as e:
        return f"Error: {str(e)}"

if __name__ == "__main__":
    mcp.run()


# uv run mcpo --port 8001 -- uv run main.py