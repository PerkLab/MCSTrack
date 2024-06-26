from .mct_request import MCTRequest
from pydantic import BaseModel, Field


class MCTRequestSeries(BaseModel):
    series: list[MCTRequest] = Field()
