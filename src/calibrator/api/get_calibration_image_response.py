from src.common import MCTResponse
from pydantic import Field


class GetCalibrationImageResponse(MCTResponse):
    @staticmethod
    def parsable_type_identifier() -> str:
        return "get_calibration_image"

    parsable_type: str = Field(default=parsable_type_identifier(), const=True)
    image_base64: str = Field()
