"""Compatibility launcher; application lives in src/montralog."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent/"src"))
from montralog.cli import main
if __name__ == "__main__":
    main()
