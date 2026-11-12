"""Entry point: python -m nfl_lab [run|--check]"""
import sys

from .engine import run

if __name__ == "__main__":
    run(check="--check" in sys.argv)
