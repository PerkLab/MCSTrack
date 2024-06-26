from src.common import MCTRequest
from pydantic import Field


class SetReferenceMarkerRequest(MCTRequest):
    @staticmethod
    def parsable_type_identifier() -> str:
        return "set_reference_marker"

    parsable_type: str = Field(default=parsable_type_identifier(), const=True)
    marker_id: int = Field()
    marker_diameter: float = Field()
