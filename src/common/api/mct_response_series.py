from .mct_response import MCTResponse
from pydantic import BaseModel, Field


class MCTResponseSeries(BaseModel):
    series: list[MCTResponse] = Field(default=list())
    responder: str = Field(default=str())
