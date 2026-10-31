"""Typed transcript data models."""
from pydantic import BaseModel, Field

class Segment(BaseModel):
    start: float = Field(ge=0)
    duration: float = Field(ge=0)
    text: str
    @property
    def end(self) -> float:
        return self.start + self.duration

class Transcript(BaseModel):
    source_url: str
    title: str | None = None
    language: str = "und"
    language_name: str | None = None
    source: str = "unknown"
    segments: list[Segment] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    @property
    def text(self) -> str:
        return " ".join(s.text.strip() for s in self.segments if s.text.strip()).strip()
    @property
    def duration(self) -> float:
        return max((s.end for s in self.segments), default=0.0)
