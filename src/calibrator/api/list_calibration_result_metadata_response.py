from ..structures import CalibrationResultMetadata
from src.common import MCTResponse
from pydantic import Field


class ListCalibrationResultMetadataResponse(MCTResponse):
    @staticmethod
    def parsable_type_identifier() -> str:
        return "get_calibration_result_metadata_list"

    parsable_type: str = Field(default=parsable_type_identifier(), const=True)
    metadata_list: list[CalibrationResultMetadata] = Field(default_factory=list)
