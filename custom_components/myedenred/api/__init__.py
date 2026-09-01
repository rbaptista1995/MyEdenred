"""The my_edenred component."""

import json
from pathlib import Path

__version__ = json.loads(Path(__file__).parents[1].joinpath("manifest.json").read_text(encoding="utf-8"))["version"]
