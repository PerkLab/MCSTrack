from src.common import MCTRequest
from pydantic import Field


class StopCaptureRequest(MCTRequest):
    @staticmethod
    def parsable_type_identifier() -> str:
        return "stop_capture"

    parsable_type: str = Field(default=parsable_type_identifier(), const=True)
