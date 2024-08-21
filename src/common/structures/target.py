import abc
import numpy
from pydantic import BaseModel, Field, PrivateAttr


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
    def get_points_for_marker_id(self, marker_id: str) -> list[list[float]]: ...

    @abc.abstractmethod
    def get_points(self) -> list[list[float]]: ...


class TargetMarker(TargetBase, Marker):
    def get_marker_ids(self) -> list[str]:
        return [self.marker_id]

    def get_points(self) -> list[list[float]]:
        return self.get_points_internal()

    def get_points_for_marker_id(self, marker_id: str) -> list[list[float]]:
        if marker_id != self.marker_id:
            raise IndexError(f"marker_id {marker_id} is not in target {self.target_id}")
        return self.get_points_internal()


class TargetBoard(TargetBase):
    markers: list[Marker] = Field()
    _marker_dict: None | dict[str, Marker] = PrivateAttr()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._marker_dict = None

    def get_marker_ids(self) -> list[str]:
        return [marker.marker_id for marker in self.markers]

    def get_points(self) -> list[list[float]]:
        points = list()
        for marker in self.markers:
            points += marker.get_points_internal()
        return points

    def get_points_for_marker_id(self, marker_id: str) -> list[list[float]]:
        if self._marker_dict is None:
            self._marker_dict = dict()
            for marker in self.markers:
                self._marker_dict[marker.marker_id] = marker
        if marker_id not in self._marker_dict:
            raise IndexError(f"marker_id {marker_id} is not in target {self.target_id}")
        return self._marker_dict[marker_id].points
