from .mct_response import MCTResponse
from src.common.structures.status_message import StatusMessage
from pydantic import Field


class DequeueStatusMessagesResponse(MCTResponse):

    @staticmethod
    def parsable_type_identifier() -> str:
        return "dequeue_status_message"

    parsable_type: str = Field(default=parsable_type_identifier(), const=True)

    status_messages: list[StatusMessage] = Field()
