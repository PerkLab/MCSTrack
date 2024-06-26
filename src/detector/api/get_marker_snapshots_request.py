from src.common import MCTRequest
from pydantic import Field


class GetMarkerSnapshotsRequest(MCTRequest):
    @staticmethod
    def parsable_type_identifier() -> str:
        return "get_marker_snapshots"

    parsable_type: str = Field(default=parsable_type_identifier(), const=True)
    include_detected: bool = Field(default=True)
    include_rejected: bool = Field(default=True)
