from src.common import MCTRequest
from pydantic import Field


class ListCalibrationDetectorResolutionsRequest(MCTRequest):
    @staticmethod
    def parsable_type_identifier() -> str:
        return "list_calibration_detector_resolutions"

    parsable_type: str = Field(default=parsable_type_identifier(), const=True)
