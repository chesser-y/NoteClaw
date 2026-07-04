from __future__ import annotations

from pathlib import Path
from sqlite3 import Connection, connect


class SQLiteStore:
    """Thin SQLite connection factory.

    Schema creation and repositories will be implemented on top of this class.
    """

    def __init__(self, path: Path) -> None:
        self.path = path

    def connect(self) -> Connection:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        conn = connect(self.path)
        conn.row_factory = None
        return conn
