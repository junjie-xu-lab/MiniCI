"""SQLite schema and execution history repository."""

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from minici.core.results import PipelineResult

SCHEMA_VERSION = 1


class RunRepository:
    def __init__(self, path: Path) -> None:
        self.path = path

    def connect(self) -> sqlite3.Connection:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(self.path, timeout=10)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA journal_mode = WAL")
        connection.execute("PRAGMA busy_timeout = 10000")
        return connection

    def initialize(self) -> None:
        with self.connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS schema_info (
                    version INTEGER NOT NULL
                );
                CREATE TABLE IF NOT EXISTS runs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    run_uid TEXT NOT NULL UNIQUE,
                    project TEXT NOT NULL,
                    status TEXT NOT NULL,
                    started_at TEXT NOT NULL,
                    ended_at TEXT,
                    duration REAL,
                    run_directory TEXT NOT NULL,
                    summary_json TEXT
                );
                CREATE TABLE IF NOT EXISTS stages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    run_id INTEGER NOT NULL REFERENCES runs(id) ON DELETE CASCADE,
                    position INTEGER NOT NULL,
                    name TEXT NOT NULL,
                    status TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS steps (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    stage_id INTEGER NOT NULL REFERENCES stages(id) ON DELETE CASCADE,
                    position INTEGER NOT NULL,
                    name TEXT NOT NULL,
                    status TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS attempts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    step_id INTEGER NOT NULL REFERENCES steps(id) ON DELETE CASCADE,
                    number INTEGER NOT NULL,
                    status TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS commands (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    attempt_id INTEGER NOT NULL REFERENCES attempts(id) ON DELETE CASCADE,
                    position INTEGER NOT NULL,
                    command TEXT NOT NULL,
                    status TEXT NOT NULL,
                    exit_code INTEGER,
                    duration REAL NOT NULL,
                    stdout_summary TEXT NOT NULL,
                    stderr_summary TEXT NOT NULL
                );
                """
            )
            row = connection.execute("SELECT version FROM schema_info").fetchone()
            if row is None:
                connection.execute("INSERT INTO schema_info(version) VALUES (?)", (SCHEMA_VERSION,))
            elif row["version"] != SCHEMA_VERSION:
                raise RuntimeError(f"unsupported database schema version: {row['version']}")

    def start_run(self, project: str, run_root: Path) -> tuple[int, str, Path]:
        self.initialize()
        run_uid = str(uuid4())
        run_directory = run_root / run_uid
        run_directory.mkdir(parents=True, exist_ok=False)
        with self.connect() as connection:
            cursor = connection.execute(
                "INSERT INTO runs(run_uid, project, status, started_at, run_directory) "
                "VALUES (?, ?, 'RUNNING', ?, ?)",
                (run_uid, project, datetime.now(timezone.utc).isoformat(), str(run_directory)),
            )
            return int(cursor.lastrowid), run_uid, run_directory

    def finish_run(self, result: PipelineResult) -> None:
        duration = (result.ended_at - result.started_at).total_seconds()
        summary = {
            "stages": [
                {
                    "name": stage.name,
                    "status": stage.status.value,
                    "steps": [
                        {"name": step.name, "status": step.status.value} for step in stage.steps
                    ],
                }
                for stage in result.stages
            ]
        }
        with self.connect() as connection:
            connection.execute(
                "UPDATE runs SET status=?, ended_at=?, duration=?, summary_json=? WHERE id=?",
                (
                    result.status.value,
                    result.ended_at.isoformat(),
                    duration,
                    json.dumps(summary),
                    result.run_id,
                ),
            )
            for stage_position, stage in enumerate(result.stages):
                stage_cursor = connection.execute(
                    "INSERT INTO stages(run_id, position, name, status) VALUES (?, ?, ?, ?)",
                    (result.run_id, stage_position, stage.name, stage.status.value),
                )
                for step_position, step in enumerate(stage.steps):
                    step_cursor = connection.execute(
                        "INSERT INTO steps(stage_id, position, name, status) VALUES (?, ?, ?, ?)",
                        (stage_cursor.lastrowid, step_position, step.name, step.status.value),
                    )
                    for attempt in step.attempts:
                        attempt_cursor = connection.execute(
                            "INSERT INTO attempts(step_id, number, status) VALUES (?, ?, ?)",
                            (step_cursor.lastrowid, attempt.number, attempt.status.value),
                        )
                        for command_position, command in enumerate(attempt.commands):
                            connection.execute(
                                """INSERT INTO commands(
                                attempt_id, position, command, status, exit_code, duration,
                                stdout_summary, stderr_summary
                                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                                (
                                    attempt_cursor.lastrowid,
                                    command_position,
                                    command.command,
                                    command.status.value,
                                    command.exit_code,
                                    command.duration,
                                    command.stdout[-4000:],
                                    command.stderr[-4000:],
                                ),
                            )

    def recent(self, limit: int = 10) -> list[sqlite3.Row]:
        self.initialize()
        with self.connect() as connection:
            return list(connection.execute("SELECT * FROM runs ORDER BY id DESC LIMIT ?", (limit,)))

    def fail_run(self, run_id: int, status: str = "INTERRUPTED") -> None:
        with self.connect() as connection:
            connection.execute(
                "UPDATE runs SET status=?, ended_at=? WHERE id=? AND status='RUNNING'",
                (status, datetime.now(timezone.utc).isoformat(), run_id),
            )

    def details(self, run_id: int) -> dict[str, object] | None:
        self.initialize()
        with self.connect() as connection:
            run = connection.execute("SELECT * FROM runs WHERE id=?", (run_id,)).fetchone()
            if run is None:
                return None
            stages = connection.execute(
                "SELECT * FROM stages WHERE run_id=? ORDER BY position", (run_id,)
            ).fetchall()
            return {"run": dict(run), "stages": [dict(stage) for stage in stages]}
