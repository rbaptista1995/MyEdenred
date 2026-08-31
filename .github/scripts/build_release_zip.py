"""Build the HACS release asset (myedenred.zip).

HACS extracts zip_release assets directly into
config/custom_components/<domain>/, so the archive must contain the
integration files at its root (no custom_components/ prefix).
"""

import sys
import zipfile
from pathlib import Path

SOURCE_DIR = Path("custom_components/myedenred")
OUTPUT_ZIP = Path("dist/myedenred.zip")
REQUIRED_FILES = ("manifest.json", "__init__.py")
EXCLUDED_NAMES = {".DS_Store", "Thumbs.db"}
EXCLUDED_SUFFIXES = (".pyc", ".pyo", ".tmp")
EXCLUDED_DIRS = {"__pycache__", ".mypy_cache", ".pytest_cache"}


def collect_files():
    if not SOURCE_DIR.is_dir():
        sys.exit(f"error: integration source directory '{SOURCE_DIR}' not found")

    for required in REQUIRED_FILES:
        if not (SOURCE_DIR / required).is_file():
            sys.exit(f"error: required file '{SOURCE_DIR / required}' is missing")

    files = []
    for path in sorted(SOURCE_DIR.rglob("*")):
        if not path.is_file():
            continue
        relative = path.relative_to(SOURCE_DIR)
        if any(part in EXCLUDED_DIRS for part in relative.parts[:-1]):
            continue
        if path.name in EXCLUDED_NAMES or path.suffix in EXCLUDED_SUFFIXES:
            continue
        files.append(path)

    if not files:
        sys.exit("error: no files collected for the release archive")
    return files


def main():
    files = collect_files()
    OUTPUT_ZIP.parent.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(OUTPUT_ZIP, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in files:
            archive.write(path, path.relative_to(SOURCE_DIR).as_posix())

    print(f"Created {OUTPUT_ZIP} with {len(files)} file(s):")
    with zipfile.ZipFile(OUTPUT_ZIP) as archive:
        for name in archive.namelist():
            print(f"  {name}")


if __name__ == "__main__":
    main()
