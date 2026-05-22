"""Reset the local Midas database (delete + recreate)."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from midas.config import load_config
from midas.repositories.database import DatabaseManager


def main() -> None:
    config = load_config()
    db_path = config.db_path

    if db_path.exists():
        db_path.unlink()
        print(f"刪除: {db_path}")

    mgr = DatabaseManager(db_path=str(db_path))
    mgr.init()
    print(f"重建空白資料庫: {db_path}")


if __name__ == "__main__":
    main()
