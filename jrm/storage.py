"""Transactional local sessions. SQLite is canonical; CSV/JSON exports are portable."""
import csv
import json
import sqlite3
import uuid
from pathlib import Path
from platformdirs import user_data_dir


def default_data_dir():
    return Path(user_data_dir("JawRecoveryMonitor", appauthor=False))

class Storage:
    def __init__(self, root=None):
        self.root = Path(root) if root else default_data_dir()
        self.root.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(self.root / "sessions.sqlite3")
        self.db.execute("PRAGMA foreign_keys=ON")
        self.db.execute("PRAGMA journal_mode=WAL")
        self.db.executescript('''
        CREATE TABLE IF NOT EXISTS participants(id TEXT PRIMARY KEY);
        CREATE TABLE IF NOT EXISTS sessions(id TEXT PRIMARY KEY, participant TEXT NOT NULL,
            metadata TEXT NOT NULL, FOREIGN KEY(participant) REFERENCES participants(id));
        CREATE TABLE IF NOT EXISTS samples(session TEXT NOT NULL, ordinal INTEGER NOT NULL,
            data TEXT NOT NULL, PRIMARY KEY(session,ordinal),
            FOREIGN KEY(session) REFERENCES sessions(id) ON DELETE CASCADE);
        ''')
        self.db.commit()

    def participant(self):
        ident = "P-" + uuid.uuid4().hex[:12]
        with self.db:
            self.db.execute("INSERT INTO participants VALUES (?)", (ident,))
        return ident

    def participants(self):
        return [r[0] for r in self.db.execute("SELECT id FROM participants ORDER BY rowid")]

    def save(self, metadata, rows):
        # Transaction makes metadata + full sample snapshot atomic on interruption.
        sid = metadata["session_id"]
        encoded = json.dumps(metadata, allow_nan=False)
        samples = [(sid, i, json.dumps(r, allow_nan=False)) for i, r in enumerate(rows)]
        with self.db:
            self.db.execute("INSERT OR IGNORE INTO participants VALUES (?)", (metadata["participant_id"],))
            self.db.execute("INSERT INTO sessions VALUES (?,?,?) ON CONFLICT(id) DO UPDATE SET metadata=excluded.metadata",
                            (sid, metadata["participant_id"], encoded))
            self.db.execute("DELETE FROM samples WHERE session=?", (sid,))
            self.db.executemany("INSERT INTO samples VALUES (?,?,?)", samples)
        return sid

    def sessions(self, participant=None):
        query = "SELECT metadata FROM sessions"
        args = ()
        if participant:
            query += " WHERE participant=?"
            args = (participant,)
        return sorted([json.loads(r[0]) for r in self.db.execute(query, args)], key=lambda x: x["started_at"], reverse=True)

    def load(self, sid):
        row = self.db.execute("SELECT metadata FROM sessions WHERE id=?", (sid,)).fetchone()
        if row is None:
            raise KeyError("Session not found.")
        rows = [json.loads(r[0]) for r in self.db.execute("SELECT data FROM samples WHERE session=? ORDER BY ordinal", (sid,))]
        return json.loads(row[0]), rows

    def delete(self, sid):
        with self.db:
            self.db.execute("DELETE FROM sessions WHERE id=?", (sid,))

    def delete_participant(self, pid):
        with self.db:
            self.db.execute("DELETE FROM sessions WHERE participant=?", (pid,))
            self.db.execute("DELETE FROM participants WHERE id=?", (pid,))

    def export(self, sid, path):
        meta, rows = self.load(sid)
        return export_files(meta, rows, path)

    def close(self):
        self.db.close()


def export_files(meta, rows, path):
    path = Path(path).with_suffix(".csv")
    path.parent.mkdir(parents=True, exist_ok=True)
    enriched = [dict(session_id=meta["session_id"], participant_id=meta["participant_id"],
                     started_at=meta["started_at"], simulated=meta["simulated"], **r) for r in rows]
    fields = list(dict.fromkeys(k for r in enriched for k in r)) or ["session_id", "source_t", "flags"]
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(enriched)
    path.with_suffix(".json").write_text(json.dumps(meta, indent=2, allow_nan=False), encoding="utf-8")
    return path
