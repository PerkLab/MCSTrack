from .mct_request import MCTRequest
from pydantic import Field


class DequeueStatusMessagesRequest(MCTRequest):
    @staticmethod
    def parsable_type_identifier() -> str:
        return "dequeue_status_messages"

    parsable_type: str = Field(default=parsable_type_identifier(), const=True)
