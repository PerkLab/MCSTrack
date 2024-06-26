from src.common import MCTRequest
from src.common.structures import IntrinsicParameters
from pydantic import Field


class SetCaptureIntrinsicsRequest(MCTRequest):
    @staticmethod
    def parsable_type_identifier() -> str:
        return "set_capture_intrinsics"

    parsable_type: str = Field(default=parsable_type_identifier(), const=True)
    resolution_x_px: int = Field()
    resolution_y_px: int = Field()
    camera_intrinsic_parameters: IntrinsicParameters = Field()
