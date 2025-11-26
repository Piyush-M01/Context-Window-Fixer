from main import clone_github_repo
import os
import shutil

# Ensure storage is clean
if os.path.exists("storage"):
    shutil.rmtree("storage")

# Test 1: Clone a new repo
print("--- Test 1: Clone new repo ---")
repo_url = "https://github.com/rtyley/small-test-repo.git"
result = clone_github_repo(repo_url)
print(f"Result: {result}")

# Test 2: Clone existing repo (should fail gracefully)
print("\n--- Test 2: Clone existing repo ---")
result_existing = clone_github_repo(repo_url)
print(f"Result: {result_existing}")
