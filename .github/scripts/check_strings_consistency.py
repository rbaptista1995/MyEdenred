"""Check config_flow step ids, errors and abort reasons against strings.json
and translations, and validate the top-level schema keys accepted by Hassfest."""

import json
import re
import sys
from pathlib import Path

ROOT = Path("custom_components/myedenred")
ALLOWED_TOP_LEVEL = {"title", "config", "options"}

failures = []

strings = json.loads((ROOT / "strings.json").read_text(encoding="utf-8"))
translations = {
    path.stem: json.loads(path.read_text(encoding="utf-8"))
    for path in (ROOT / "translations").glob("*.json")
}

for name, doc in [("strings.json", strings), *translations.items()]:
    extra = set(doc) - ALLOWED_TOP_LEVEL
    if extra:
        failures.append(f"{name}: invalid top-level keys {sorted(extra)}")

flow = (ROOT / "config_flow.py").read_text(encoding="utf-8")
step_ids = set(re.findall(r'step_id="([a-z_]+)"', flow))
errors = set(re.findall(r'"base":\s*"([a-z_]+)"', flow))
aborts = set(re.findall(r'async_abort\(reason="([a-z_]+)"', flow))
aborts.add("already_configured")  # raised by _abort_if_unique_id_configured

def walk(name, doc):
    config = doc.get("config", {})
    steps = set(config.get("step", {}))
    errs = set(config.get("error", {}))
    abrt = set(config.get("abort", {}))
    for label, needed, have in (
        ("step", step_ids, steps),
        ("error", errors, errs),
        ("abort", aborts, abrt),
    ):
        missing = needed - have
        if missing:
            failures.append(f"{name}: missing {label} keys {sorted(missing)}")

for name, doc in [("strings.json", strings), *translations.items()]:
    walk(name, doc)

en_keys = json.dumps(sorted(translations["en"].get("config", {}).get("step", {})))
strings_keys = json.dumps(sorted(strings.get("config", {}).get("step", {})))
if en_keys != strings_keys:
    failures.append("translations/en.json steps differ from strings.json")

if failures:
    print("FAIL")
    for failure in failures:
        print(f"  {failure}")
    sys.exit(1)

print(f"OK steps={sorted(step_ids)} errors={sorted(errors)} aborts={sorted(aborts)}")
