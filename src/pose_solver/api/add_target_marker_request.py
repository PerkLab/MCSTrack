from src.common import MCTRequest
from pydantic import Field


class AddTargetMarkerRequest(MCTRequest):
    @staticmethod
    def parsable_type_identifier() -> str:
        return "add_target_marker"

    parsable_type: str = Field(default=parsable_type_identifier(), const=True)
    marker_id: int = Field()
    marker_diameter: float = Field()
