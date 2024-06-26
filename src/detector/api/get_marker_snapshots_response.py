from src.common import MCTResponse
from src.common.structures import MarkerSnapshot
from pydantic import Field


class GetMarkerSnapshotsResponse(MCTResponse):
    @staticmethod
    def parsable_type_identifier() -> str:
        return "get_marker_snapshots"

    parsable_type: str = Field(default=parsable_type_identifier(), const=True)
    detected_marker_snapshots: list[MarkerSnapshot] | None = Field()
    rejected_marker_snapshots: list[MarkerSnapshot] | None = Field()
