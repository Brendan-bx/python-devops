"""Data models — Server dataclass and Pydantic schemas."""

from dataclasses import dataclass

from pydantic import BaseModel, Field


@dataclass
class Server:
    """In-memory representation of a monitored server."""

    id: int
    name: str
    host: str
    port: int
    status: str = "unknown"

    def base_url(self) -> str:
        """Return the base HTTP URL for this server."""
        return f"http://{self.host}:{self.port}"


class ServerIn(BaseModel):
    """Payload for registering a new server."""

    name: str = Field(..., min_length=1)
    host: str
    port: int = Field(..., ge=1, le=65535)


class ServerOut(BaseModel):
    """Server as returned by the API."""

    id: int
    name: str
    host: str
    port: int
    status: str
