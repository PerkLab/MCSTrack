from src.common import MCTResponse
from pydantic import Field


class AddCalibrationImageResponse(MCTResponse):
    @staticmethod
    def parsable_type_identifier() -> str:
        return "add_calibration_image"

    parsable_type: str = Field(default=parsable_type_identifier(), const=True)
    image_identifier: str = Field()
