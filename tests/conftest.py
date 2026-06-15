import sys
import os
from dotenv import load_dotenv

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Load .env from project root before any tests run
load_dotenv(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".env")))