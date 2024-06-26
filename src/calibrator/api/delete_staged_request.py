from src.common import MCTRequest
from pydantic import Field


class DeleteStagedRequest(MCTRequest):
    @staticmethod
    def parsable_type_identifier() -> str:
        return "clear_calibration_data_staged_for_deletion"

    parsable_type: str = Field(default=parsable_type_identifier(), const=True)
