# tests/conftest.py
import sys
import os

# Add the project root directory to the Python path
# This allows tests to import modules from the main project (e.g., caldav_service)
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
