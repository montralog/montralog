"""Compatibility WSGI entry point."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent/"src"))
from montralog.wsgi import application
