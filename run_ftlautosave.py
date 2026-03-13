#!/usr/bin/env python3.11
"""
FTL Autosave for Mac
Entry point script

Usage:
    /opt/homebrew/bin/python3.11 run_ftlautosave.py

Note: Requires Python 3.11 with tkinter from Homebrew.
"""
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ftlautosave.gui import main

if __name__ == "__main__":
    main()
