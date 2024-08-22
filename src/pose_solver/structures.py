from src.common.structures import \
    DetectorFrame, \
    Matrix4x4
import cv2.aruco
import datetime
import numpy
from pydantic import BaseModel, Field
from typing import Final


EPSILON: Final[float] = 0.0001


class DetectorFrameRecord:
    _detector_label: str
    _frame: DetectorFrame
    _timestamp_utc: datetime.datetime | None
    _corners_by_marker_id: dict[str, list[list[float]]] | None

    def __init__(
        self,
        detector_label: str,
        frame: DetectorFrame
    ):
        self._detector_label = detector_label
        self._frame = frame
        self._timestamp_utc = None  # calculated when needed
        self._corners_by_marker_id = None

    def _init_corners_by_marker_id(self):
        self._corners_by_marker_id = dict()
        for snapshot in self._frame.detected_marker_snapshots:
            self._corners_by_marker_id[snapshot.label] = [
                [corner_image_point.x_px, corner_image_point.y_px]
                for corner_image_point in snapshot.corner_image_points]

    def get_detector_label(self) -> str:
        return self._detector_label

    def get_frame(self) -> DetectorFrame:
        return self._frame

    def get_marker_corners_by_marker_id(
        self,
        marker_id: str
    ) -> list[list[float]] | None:
        if self._corners_by_marker_id is None:
            self._init_corners_by_marker_id()
        if marker_id in list(self._corners_by_marker_id.keys()):
            return self._corners_by_marker_id[marker_id]
        return None

    def get_marker_ids_detected(self) -> list[str]:
        if self._corners_by_marker_id is None:
            self._init_corners_by_marker_id()
        return list(self._corners_by_marker_id.keys())

    def get_timestamp_utc(self):
        if self._timestamp_utc is None:
            self._timestamp_utc = self._frame.timestamp_utc()
        return self._timestamp_utc


class DetectorRecord:
    _frame_records_by_marker_id: dict[str, DetectorFrameRecord] = Field(default_factory=dict)

    def __init__(self):
        self._frame_records_by_marker_id = dict()

    def add_frame_record(
        self,
        frame_record: DetectorFrameRecord
    ) -> None:
        marker_ids: list[str] = frame_record.get_marker_ids_detected()
        for marker_id in marker_ids:
            if marker_id not in self._frame_records_by_marker_id or \
               frame_record.get_timestamp_utc() > self._frame_records_by_marker_id[marker_id].get_timestamp_utc():
                self._frame_records_by_marker_id[marker_id] = frame_record

    def clear_frame_records(self):
        self._frame_records_by_marker_id.clear()

    def clear_frame_records_older_than(
        self,
        timestamp_utc: datetime.datetime
    ) -> bool:
        """
        returns True if any changes were made
        """
        return_value: bool = False
        marker_ids: list[str] = list(self._frame_records_by_marker_id.keys())
        for marker_id in marker_ids:
            frame_record: DetectorFrameRecord = self._frame_records_by_marker_id[marker_id]
            if frame_record.get_timestamp_utc() < timestamp_utc:
                del self._frame_records_by_marker_id[marker_id]
                return_value = True
        return return_value

    def get_corners(
        self
    ) -> dict[str, list[list[float]]]:  # [marker_id][point_index][x/y/z]
        corners_by_marker_id: dict[str, list[list[float]]] = dict()
        for marker_id, frame_record in self._frame_records_by_marker_id.items():
            corners_by_marker_id[marker_id] = frame_record.get_marker_corners_by_marker_id(marker_id=marker_id)
        return corners_by_marker_id

    def get_corners_for_marker_id(
        self,
        marker_id: str
    ) -> list[list[float]] | None:  # [point_index][x/y/z]
        if marker_id not in self._frame_records_by_marker_id:
            return None
        return self._frame_records_by_marker_id[marker_id].get_marker_corners_by_marker_id(marker_id=marker_id)


class PoseSolverConfiguration(BaseModel):
    serial_identifier: str = Field()


class PoseSolverParameters(BaseModel):
    minimum_detector_count: int = Field(default=2)
    MAXIMUM_RAY_COUNT_FOR_INTERSECTION: int = Field(2)
    POSE_MULTI_CAMERA_LIMIT_RAY_AGE_SECONDS: float = Field(0.1)
    POSE_SINGLE_CAMERA_EXTRAPOLATION_MINIMUM_SURFACE_NORMAL_ANGLE_DEGREES: float = Field(15.0)
    POSE_SINGLE_CAMERA_EXTRAPOLATION_LIMIT_RAY_AGE_SECONDS: float = Field(1.0)
    POSE_SINGLE_CAMERA_EXTRAPOLATION_MAXIMUM_ORDER: int = Field(0)
    POSE_SINGLE_CAMERA_EXTRAPOLATION_LIMIT_ANGLE_DEGREES: float = Field(15.0)
    POSE_SINGLE_CAMERA_EXTRAPOLATION_LIMIT_DISTANCE: float = Field(15.0, description="millimeters")
    POSE_SINGLE_CAMERA_NEAREST_LIMIT_RAY_AGE_SECONDS: float = Field(0.8)
    POSE_SINGLE_CAMERA_NEAREST_LIMIT_ANGLE_DEGREES: float = Field(15.0)
    POSE_SINGLE_CAMERA_NEAREST_LIMIT_DISTANCE: float = Field(15.0)
    POSE_SINGLE_CAMERA_REPROJECTION_ERROR_FACTOR_BETA_OVER_ALPHA: float = Field(1.0)
    POSE_SINGLE_CAMERA_DEPTH_LIMIT_AGE_SECONDS: float = Field(0.4)
    # TODO: Is this next one detector-specific?
    POSE_SINGLE_CAMERA_DEPTH_CORRECTION: float = Field(-7.5, description="millimeters, observed tendency to overestimate depth.")
    POSE_DETECTOR_DENOISE_LIMIT_AGE_SECONDS: float = Field(1.0)
    INTERSECTION_MAXIMUM_DISTANCE: float = Field(10.0, description="millimeters")
    icp_termination_iteration_count: int = Field(50)
    icp_termination_translation: float = Field(0.005, description="millimeters")
    icp_termination_rotation_radians: float = Field(0.0005)
    icp_termination_mean_point_distance: float = Field(0.1, description="millimeters")
    icp_termination_rms_point_distance: float = Field(0.1, description="millimeters")
    DENOISE_OUTLIER_DISTANCE_MILLIMETERS: float = Field(10.0)
    DENOISE_OUTLIER_ANGLE_DEGREES: float = Field(5.0)
    DENOISE_STORAGE_SIZE: int = Field(10)
    DENOISE_FILTER_SIZE: int = Field(7)
    DENOISE_REQUIRED_STARTING_STREAK: int = Field(3)
    ARUCO_MARKER_DICTIONARY_ENUM: int = Field(cv2.aruco.DICT_4X4_100)
    ARUCO_POSE_ESTIMATOR_METHOD: int = Field(cv2.SOLVEPNP_ITERATIVE)
    # SOLVEPNP_ITERATIVE works okay but is susceptible to optical illusions (flipping)
    # SOLVEPNP_P3P appears to return nan's on rare occasion
    # SOLVEPNP_SQPNP appears to return nan's on rare occasion
    # SOLVEPNP_IPPE_SQUARE does not seem to work very well at all, translation is much smaller than expected


class Ray:
    source_point: list[float]
    direction: list[float]

    def __init__(
        self,
        source_point: list[float],
        direction: list[float]
    ):
        direction_norm = numpy.linalg.norm(direction)
        if direction_norm < EPSILON:
            raise ValueError("Direction cannot be zero.")
        self.source_point = source_point
        self.direction = direction
