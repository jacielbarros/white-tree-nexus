"""Schemas de sugestoes heuristicas."""

from pydantic import BaseModel


class SuggestionResponse(BaseModel):
    id: str
    target: str
    payload: dict
    reason: str


class SuggestionAccept(BaseModel):
    suggestion_id: str
