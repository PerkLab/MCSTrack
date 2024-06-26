from ..structures import CalibrationResultState
from src.common import MCTRequest
from pydantic import Field


class UpdateCalibrationResultMetadataRequest(MCTRequest):
    @staticmethod
    def parsable_type_identifier() -> str:
        return "update_calibration_result_metadata"

    parsable_type: str = Field(default=parsable_type_identifier(), const=True)
    result_identifier: str = Field()
    result_state: CalibrationResultState = Field()
