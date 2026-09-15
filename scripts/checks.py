"""Run the repository's fast, service-free checks."""

import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CHECKS = (
    (sys.executable, "-m", "ruff", "check", "."),
    (sys.executable, "-m", "ruff", "check", "tests", "--select", "E4,E7,E9,F,I"),
    (sys.executable, "-m", "ruff", "format", "--check", "tests"),
    (sys.executable, "-m", "pytest", "-q"),
    (sys.executable, "-c", "from main import app; assert app.routes"),
)


def main() -> int:
    for command in CHECKS:
        print(f"Running: {' '.join(command)}", flush=True)
        result = subprocess.run(command, cwd=ROOT, check=False)
        if result.returncode:
            return result.returncode
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
