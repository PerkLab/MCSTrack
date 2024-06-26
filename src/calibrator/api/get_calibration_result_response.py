from src.common import MCTResponse
from src.common.structures import IntrinsicCalibration
from pydantic import Field


class GetCalibrationResultResponse(MCTResponse):
    @staticmethod
    def parsable_type_identifier() -> str:
        return "get_calibration_result"

    parsable_type: str = Field(default=parsable_type_identifier(), const=True)
    intrinsic_calibration: IntrinsicCalibration = Field()
