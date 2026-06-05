#!/usr/bin/env python
"""Direct Flask app runner - no debug mode"""
import sys
import os

# Make sure we're in the right directory
os.chdir(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.getcwd())

from app import app

if __name__ == "__main__":
    print(f"🚀 Starting Flask app from: {os.getcwd()}")
    print(f"App module file: {app.__module__}")
    app.run(port=5000, debug=False)
