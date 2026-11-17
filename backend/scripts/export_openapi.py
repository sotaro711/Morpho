import json
from pathlib import Path

from s4web.presentation.app import create_app

OUT = Path(__file__).resolve().parents[2] / "openapi.json"


def main() -> None:
    app = create_app()
    schema = app.openapi()
    OUT.write_text(json.dumps(schema, indent=2, ensure_ascii=False) + "\n")
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
