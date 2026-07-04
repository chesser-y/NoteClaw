from __future__ import annotations

from typing import Protocol

from noteclaw_backend.schemas.knowledge import NoteDetail, NoteListItem


class NoteRepository(Protocol):
    async def create_note(self, note: NoteDetail) -> None:
        ...

    async def get_note(self, note_id: str) -> NoteDetail | None:
        ...

    async def list_notes(self, limit: int, offset: int) -> tuple[list[NoteListItem], int]:
        ...

    async def delete_note(self, note_id: str) -> None:
        ...


class ChunkRepository(Protocol):
    async def list_by_note(self, note_id: str) -> list[dict]:
        ...

    async def get_by_ids(self, chunk_ids: list[str]) -> list[dict]:
        ...
