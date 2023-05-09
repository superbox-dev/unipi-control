import os
from pathlib import Path

version: str = Path("version.txt").read_text(encoding="utf-8").replace("\n", "")
__version__ = os.environ.get("PACKAGE_VERSION", version)
