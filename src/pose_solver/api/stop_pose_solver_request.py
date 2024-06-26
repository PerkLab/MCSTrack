from src.common import MCTRequest
from pydantic import Field


class StopPoseSolverRequest(MCTRequest):
    @staticmethod
    def parsable_type_identifier() -> str:
        return "stop_pose_solver"

    parsable_type: str = Field(default=parsable_type_identifier(), const=True)
