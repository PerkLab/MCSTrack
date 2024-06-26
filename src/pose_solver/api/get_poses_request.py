from src.common import MCTRequest
from pydantic import Field


class GetPosesRequest(MCTRequest):
    @staticmethod
    def parsable_type_identifier() -> str:
        return "get_poses"

    parsable_type: str = Field(default=parsable_type_identifier(), const=True)
