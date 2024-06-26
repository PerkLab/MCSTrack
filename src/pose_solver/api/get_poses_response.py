from src.common import MCTResponse
from src.common.structures import Pose
from pydantic import Field


class GetPosesResponse(MCTResponse):
    @staticmethod
    def parsable_type_identifier() -> str:
        return "get_poses"

    parsable_type: str = Field(default=parsable_type_identifier(), const=True)
    detector_poses: list[Pose]
    target_poses: list[Pose]
