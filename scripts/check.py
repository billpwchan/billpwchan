"""Fail the run if any rendered SVG is not well-formed XML (a malformed card shows as a broken image on GitHub)."""
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

EXPECTED = ["hero", "regime", "risk", "derivatives", "activity", "recent", "snake", "strip-work", "strip-lab", "strip-flow",
            "work-futu_algo", "work-futu_tick_downloader", "work-strategy_powerbacktest", "work-DeepTrust",
            "key-web", "key-in", "key-mail", "key-ig", "key-gh"]

out = Path(sys.argv[1] if len(sys.argv) > 1 else "dist")
bad = []
for f in sorted(out.glob("*.svg")):
    try:
        ET.parse(f)
    except ET.ParseError as e:
        bad.append(f"{f.name}: {e}")
missing = [n for n in EXPECTED if not (out / f"{n}.svg").exists()]
if missing:
    print("warning: not rendered yet:", ", ".join(missing))
if bad:
    sys.exit("malformed SVG:\n" + "\n".join(bad))
print(f"{len(list(out.glob('*.svg')))} SVGs well-formed")
