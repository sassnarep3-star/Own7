"""One-command, noninteractive research build."""
import argparse
from .engine import run

parser = argparse.ArgumentParser(description="Reproduce frozen OWN7 research; never place bets")
parser.add_argument("command", choices=["run"])
parser.add_argument("--check", action="store_true", help="Fail if committed results differ")
args = parser.parse_args()
run(check=args.check)
