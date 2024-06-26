from src.common import MCTRequest
from pydantic import Field


class GetCalibrationResultRequest(MCTRequest):
    @staticmethod
    def parsable_type_identifier() -> str:
        return "get_calibration_result"

    parsable_type: str = Field(default=parsable_type_identifier(), const=True)
    result_identifier: str = Field()
