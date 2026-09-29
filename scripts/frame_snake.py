"""Wrap the Platane/snk render in the terminal panel frame: dist/snake-raw.svg -> dist/snake.svg."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import cards  # noqa: E402
from generate import BOOT  # noqa: E402
from theme import boot  # noqa: E402

out = Path(sys.argv[1] if len(sys.argv) > 1 else "dist")
raw = out / "snake-raw.svg"
if raw.exists():
    (out / "snake.svg").write_text(boot(cards.snake_panel(raw.read_text()), BOOT["snake"]))
    raw.unlink()
    print("wrote snake.svg")
else:
    print("no snake render this run; keeping previous snake.svg")
