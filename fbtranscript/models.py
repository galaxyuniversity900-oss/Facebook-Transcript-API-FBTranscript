"""Small dependency-free transcript data models shared by all runtimes."""
from dataclasses import asdict, dataclass


@dataclass
class Segment:
    start: float
    duration: float
    text: str

    @property
    def end(self) -> float:
        return self.start + self.duration

    def model_dump(self) -> dict:
        return asdict(self)


@dataclass
class Transcript:
    source_url: str
    title: str | None = None
    language: str = "und"
    language_name: str | None = None
    source: str = "unknown"
    segments: list[Segment] | None = None
    warnings: list[str] | None = None

    def __post_init__(self):
        if self.segments is None:
            self.segments = []
        if self.warnings is None:
            self.warnings = []

    @property
    def text(self) -> str:
        return " ".join(s.text.strip() for s in self.segments if s.text.strip()).strip()

    @property
    def duration(self) -> float:
        return max((s.end for s in self.segments), default=0.0)

    def model_dump(self) -> dict:
        return asdict(self)
