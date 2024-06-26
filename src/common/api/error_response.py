from .mct_response import MCTResponse
from pydantic import Field


class ErrorResponse(MCTResponse):
    @staticmethod
    def parsable_type_identifier() -> str:
        return "error"

    parsable_type = Field(default=parsable_type_identifier(), const=True)

    message: str = Field()
