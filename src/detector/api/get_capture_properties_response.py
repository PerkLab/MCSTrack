from src.common import MCTResponse
from pydantic import Field


class GetCapturePropertiesResponse(MCTResponse):
    @staticmethod
    def parsable_type_identifier() -> str:
        return "get_capture_properties"

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
    backlight_compensation: bool | None = Field(default=None)
    powerline_frequency_hz: int | None = Field(default=None)
