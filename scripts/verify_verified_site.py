"""Compatibility entrypoint for consolidated site checks."""
import runpy
from pathlib import Path
runpy.run_path(str(Path(__file__).with_name('check_site.py')),run_name='__main__')
