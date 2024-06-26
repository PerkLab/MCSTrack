from ..structures import CalibrationImageState
from src.common import MCTRequest
from pydantic import Field


class UpdateCalibrationImageMetadataRequest(MCTRequest):
    @staticmethod
    def parsable_type_identifier() -> str:
        return "update_calibration_image_metadata"

    parsable_type: str = Field(default=parsable_type_identifier(), const=True)
    image_identifier: str = Field()
    image_state: CalibrationImageState = Field()
    image_label: str = Field()
