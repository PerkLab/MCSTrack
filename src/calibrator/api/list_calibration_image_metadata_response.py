from ..structures import CalibrationImageMetadata
from src.common import MCTResponse
from pydantic import Field


class ListCalibrationImageMetadataResponse(MCTResponse):
    @staticmethod
    def parsable_type_identifier() -> str:
        return "get_calibration_metadata_identifier_list"

    parsable_type: str = Field(default=parsable_type_identifier(), const=True)
    metadata_list: list[CalibrationImageMetadata] = Field(default_factory=list)
