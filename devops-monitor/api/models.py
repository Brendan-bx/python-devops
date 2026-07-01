"""Domain models and Pydantic schemas."""

from dataclasses import dataclass, field

from pydantic import BaseModel, Field


@dataclass
class Server:
    """Registered server tracked by the monitoring API."""

    id: int
    name: str
    host: str
    port: int
    status: str = field(default="UNKNOWN")

    def base_url(self) -> str:
        """Build the HTTP base URL for this server."""
        return f"http://{self.host}:{self.port}"


class ServerIn(BaseModel):
    """Payload for registering a new server."""

    name: str = Field(..., min_length=1)
    host: str = Field(..., min_length=1)
    port: int = Field(..., ge=1, le=65535)


class ServerOut(BaseModel):
    """Server representation returned by the API."""

    id: int
    name: str
    host: str
    port: int
    status: str

    @classmethod
    def from_server(cls, server: Server) -> "ServerOut":
        """Create a response model from a ``Server`` dataclass."""
        return cls(
            id=server.id,
            name=server.name,
            host=server.host,
            port=server.port,
            status=server.status,
        )
