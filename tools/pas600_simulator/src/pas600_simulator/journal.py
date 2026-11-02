"""Crash-safe local state; generation evidence is separate from mutable transfer state."""
import json
import os
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal
from uuid import UUID, uuid4
from pydantic import BaseModel


def atomic_json(path: Path, value: dict) -> None:
    """Fsync a same-directory temporary file, atomically replace and fsync parent.

    Propagate I/O errors; failed replacement leaves the prior complete file intact.
    """
    fd, name = tempfile.mkstemp(prefix='.' + path.name, dir=path.parent)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as stream:
            json.dump(value, stream, ensure_ascii=False, allow_nan=False, sort_keys=True)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(name, path)
        parent = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(parent)
        finally:
            os.close(parent)
    finally:
        if os.path.exists(name):
            os.unlink(name)


class LocalRun(BaseModel):
    """Real run identity/state; generating is never recovered as completed implicitly."""
    id: UUID
    logical_hash: str
    created_at: datetime
    data_path: str
    control_path: str
    state: Literal['generating', 'generated', 'publishing', 'stopped', 'completed', 'failed']

    @classmethod
    def create(cls, root: Path, logical_hash: str):
        """Reserve new/empty output and persist generating state before writing data."""
        root.mkdir(parents=True, exist_ok=True)
        if any(root.iterdir()):
            raise ValueError('output must be new or empty')
        (root / 'control').mkdir()
        (root / 'data').mkdir()
        run = cls(id=uuid4(), logical_hash=logical_hash, created_at=datetime.now(UTC),
            data_path=str(root / 'data'), control_path=str(root / 'control'), state='generating')
        run.save()
        return run

    def save(self) -> None:
        """Persist only mutable run state; never overwrite generated native evidence."""
        atomic_json(Path(self.control_path) / 'run.json', self.model_dump(mode='json'))
