from src.common import MCTResponse
from src.common.structures import IntrinsicCalibration
from pydantic import Field


class CalibrateResponse(MCTResponse):
    @staticmethod
    def parsable_type_identifier() -> str:
        return "calibrate"

    parsable_type: str = Field(default=parsable_type_identifier(), const=True)
    result_identifier: str = Field()
    intrinsic_calibration: IntrinsicCalibration = Field()
