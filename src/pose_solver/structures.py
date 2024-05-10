import abc
from src.common.structures import Matrix4x4
import cv2.aruco
import datetime
import numpy
from pydantic import BaseModel, Field
from typing import Final


EPSILON: Final[float] = 0.0001


# TODO: Merge into a similar structure in common
class MarkerCorners:
    detector_label: str
    marker_id: str
    points: list[list[float]]
    timestamp: datetime.datetime

    def __init__(
        self,
        detector_label: str,
        marker_id: str,
        points: list[list[float]],
        timestamp: datetime.datetime
    ):
        self.detector_label = detector_label
        self.marker_id = marker_id
        self.points = points
        self.timestamp = timestamp


class MarkerRaySet(BaseModel):
    marker_id: int = Field()
    image_points: list[list[float]] = Field()  # image positions of marker corners. Size 4.
    image_timestamp: datetime.datetime = Field()
    ray_origin_reference: list[float] = Field()  # Shared origin for all rays (same detector)
    ray_directions_reference: list[list[float]] = Field()  # Size 4 (one for each image point)
    detector_label: str = Field()
    detector_to_reference_matrix: Matrix4x4 = Field()

    @staticmethod
    def age_seconds(
        marker_ray_set,
        query_timestamp: datetime.datetime
    ):
        return (query_timestamp - marker_ray_set.image_timestamp).total_seconds()

    @staticmethod
    def newest_timestamp_in_list(marker_ray_set_list: list) -> datetime.datetime:
        return_value = datetime.datetime.now()
        for ray_set in marker_ray_set_list:
            if ray_set.image_timestamp > return_value:
                return_value = ray_set.image_timestamp
        return return_value

    @staticmethod
    def oldest_timestamp_in_list(marker_ray_set_list: list) -> datetime.datetime:
        return_value = datetime.datetime.utcfromtimestamp(0)
        for ray_set in marker_ray_set_list:
            if ray_set.image_timestamp > return_value:
                return_value = ray_set.image_timestamp
        return return_value


# TODO: Merge/replace this with pose under common data structures
class PoseData(BaseModel):
    target_id: str = Field()
    object_to_reference_matrix: Matrix4x4 = Field()
    ray_sets: list[MarkerRaySet]

    def newest_timestamp(self) -> datetime.datetime:
        return MarkerRaySet.newest_timestamp_in_list(self.ray_sets)

    def oldest_timestamp(self) -> datetime.datetime:
        return MarkerRaySet.oldest_timestamp_in_list(self.ray_sets)

    @staticmethod
    def age_seconds(
        pose,
        query_timestamp: datetime.datetime
    ) -> float:
        return (query_timestamp - pose.oldest_timestamp()).total_seconds()


class PoseSolverConfiguration(BaseModel):
    serial_identifier: str = Field()


class PoseSolverParameters(BaseModel):
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
    ITERATIVE_CLOSEST_POINT_TERMINATION_ITERATION_COUNT: int = Field(50)
    ITERATIVE_CLOSEST_POINT_TERMINATION_TRANSLATION: float = Field(0.005, description="millimeters")
    ITERATIVE_CLOSEST_POINT_TERMINATION_ROTATION_RADIANS: float = Field(0.0005)
    ITERATIVE_CLOSEST_POINT_TERMINATION_MEAN_POINT_DISTANCE: float = Field(0.1, description="millimeters")
    ITERATIVE_CLOSEST_POINT_TERMINATION_RMS_POINT_DISTANCE: float = Field(0.1, description="millimeters")
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


class Marker(BaseModel):
    marker_id: str = Field()
    marker_size: float | None = Field(default=None)
    points: list[list[float]] | None = Field(default=None)

    # TODO: During validation, make sure either marker_size or points is defined, but not both.

    def get_marker_size(self) -> float:
        if self.marker_size is None:
            if self.points is None or len(self.points) < 2:
                raise RuntimeError("TargetMarker defined with neither marker_size nor enough points.")
            marker_size_sum: float = 0.0
            for point_index in range(0, len(self.points)):
                point_a: numpy.ndarray = numpy.asarray(self.points[point_index])
                point_b: numpy.ndarray = numpy.asarray(self.points[point_index-1])
                vector: numpy.ndarray = point_a - point_b
                marker_size_sum += numpy.linalg.norm(vector)
            self.marker_size = marker_size_sum / len(self.points)
        return self.marker_size

    def get_points_internal(self) -> list[list[float]]:
        # Use the TargetBase.get_points() instead.
        if self.points is None:
            if self.marker_size is None:
                raise RuntimeError("TargetMarker defined with neither marker_size nor points.")
            half_width = self.marker_size / 2.0
            self.points = [
                [-half_width, half_width, 0.0],
                [half_width, half_width, 0.0],
                [half_width, -half_width, 0.0],
                [-half_width, -half_width, 0.0]]
        return self.points


class TargetBase(BaseModel, abc.ABC):
    target_id: str = Field()

    @abc.abstractmethod
    def get_marker_ids(self) -> list[str]: ...

    @abc.abstractmethod
    def get_points(self) -> list[list[float]]: ...


class TargetMarker(TargetBase, Marker):
    def get_marker_ids(self) -> list[str]:
        return [self.marker_id]

    def get_points(self) -> list[list[float]]:
        return self.get_points_internal()


class TargetBoard(TargetBase):
    markers: list[Marker] = Field()

    def get_marker_ids(self) -> list[str]:
        return [marker.marker_id for marker in self.markers]

    def get_points(self) -> list[list[float]]:
        points = list()
        for marker in self.markers:
            points += marker.get_points_internal()
        return points
