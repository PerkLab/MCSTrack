from src.common import MCTRequest
from pydantic import Field


class SetCapturePropertiesRequest(MCTRequest):
    @staticmethod
    def parsable_type_identifier() -> str:
        return "set_capture_properties"

    parsable_type: str = Field(default=parsable_type_identifier(), const=True)
    resolution_x_px: int | None = Field(default=None)
    resolution_y_px: int | None = Field(default=None)
    fps: int | None = Field(default=None)
    auto_exposure: bool | None = Field(default=None)
    exposure: int | None = Field(default=None)
    brightness: int | None = Field(default=None)
    contrast: int | None = Field(default=None)
    sharpness: int | None = Field(default=None)
    gamma: int | None = Field(default=None)
