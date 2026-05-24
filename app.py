

"""
Root-level Streamlit app entry point that imports and runs the actual app from src.
"""
import sys
import os

# Ensure src is in the path
sys.path.insert(0, os.path.dirname(__file__))

# Import and run the app
from src.app import *  # noqa: F401, F403
