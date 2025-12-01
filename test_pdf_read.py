import logging
from filereader import FileReader
from config import Config
import os

# Setup logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("test")

reader = FileReader("", logger)
pdf_path = os.path.join(Config.STORAGE_PATH, "6653049d-30ee-4dca-be8c-f6ff9c1d4b17_VISAPP_2016_241.pdf")

print(f"Reading: {pdf_path}")
try:
    content = reader.read_pdf_file(pdf_path)
    print(f"Content length: {len(content)}")
    print("First 500 chars:")
    print(content[:500])
except Exception as e:
    print(f"Error: {e}")
