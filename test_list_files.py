from main import list_files

# Test with a non-existent directory
result = list_files("/path/to/non/existent/directory")
print(f"Result for non-existent directory: {result}")

# Test with a valid directory (current directory)
result_valid = list_files(".")
print(f"Result for valid directory: {result_valid}")
