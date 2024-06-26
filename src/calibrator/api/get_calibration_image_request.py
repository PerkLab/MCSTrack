from src.common import MCTRequest
from pydantic import Field


class GetCalibrationImageRequest(MCTRequest):
    @staticmethod
    def parsable_type_identifier() -> str:
        return "get_calibration_image"

    parsable_type: str = Field(default=parsable_type_identifier(), const=True)
    image_identifier: str = Field()
