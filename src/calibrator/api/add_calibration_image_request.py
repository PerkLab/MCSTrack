from src.common import MCTRequest
from src.common.structures import CaptureFormat
from pydantic import Field


class AddCalibrationImageRequest(MCTRequest):
    """
    Calibrator will infer resolution from the image itself, and associate its own label to the data.
    """
    @staticmethod
    def parsable_type_identifier() -> str:
        return "add_calibration_image"

    parsable_type: str = Field(default=parsable_type_identifier(), const=True)

    detector_serial_identifier: str = Field()
    format: CaptureFormat = Field()
    image_base64: str = Field()
