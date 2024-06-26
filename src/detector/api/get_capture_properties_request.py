from src.common import MCTRequest
from pydantic import Field


class GetCapturePropertiesRequest(MCTRequest):
    @staticmethod
    def parsable_type_identifier() -> str:
        return "get_capture_properties"

    parsable_type: str = Field(default=parsable_type_identifier(), const=True)
