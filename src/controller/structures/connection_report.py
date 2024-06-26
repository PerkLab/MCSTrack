from pydantic import BaseModel, Field


class ConnectionReport(BaseModel):
    """
    Human-readable information that shall be shown to a user about a connection.
    """
    label: str = Field()
    role: str = Field()
    ip_address: str = Field()
    port: int = Field()
    status: str = Field()

    def __eq__(self, other):
        if not isinstance(other, ConnectionReport):
            return False
        return (
            self.label == other.label and
            self.role == other.role and
            self.ip_address == other.ip_address and
            self.port == other.port and
            self.status == other.status)
