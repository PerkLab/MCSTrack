import numpy
from typing import List
from src.pose_solver.structures import Ray


EPSILON: float = 0.0001


class RayIntersection2:
    parallel: bool  # special case, mark it as such
    closest_point_1: numpy.array
    closest_point_2: numpy.array

    def __init__(
        self,
        parallel: bool,
        closest_point_1: numpy.array,
        closest_point_2: numpy.array
    ):
        self.parallel = parallel
        self.closest_point_1 = closest_point_1
        self.closest_point_2 = closest_point_2

    def centroid(self) -> numpy.array:
        return (self.closest_point_1 + self.closest_point_2) / 2

    def distance(self) -> float:
        return numpy.linalg.norm(self.closest_point_2 - self.closest_point_1)


class RayIntersectionN:
    centroids: numpy.array

    # How many rays were used.
    # Note that centroids might not use all possible intersections (e.g. parallel rays)
    ray_count: int

    def __init__(
        self,
        centroids: numpy.array,
        ray_count: int
    ):
        self.centroids = centroids
        self.ray_count = ray_count

    def centroid(self) -> numpy.array:
        sum_centroids = numpy.array([0, 0, 0], dtype="float32")
        for centroid in self.centroids:
            sum_centroids += centroid
        return sum_centroids / self.centroids.shape[0]

    def intersection_count(self) -> int:
        return int((self.ray_count * (self.ray_count - 1))/2)


def closest_intersection_between_two_lines(
    ray_1: Ray,
    ray_2: Ray
) -> RayIntersection2:  # Returns data on intersection
    ray_1_direction_normalized = ray_1.direction / numpy.linalg.norm(ray_1.direction)
    ray_2_direction_normalized = ray_2.direction / numpy.linalg.norm(ray_2.direction)

    # ray 3 will be perpendicular to both rays 1 and 2,
    # and will intersect with both rays at the nearest point(s)

    ray_3_direction = numpy.cross(ray_2_direction_normalized, ray_1_direction_normalized)
    ray_3_direction_norm = numpy.linalg.norm(ray_3_direction)
    if ray_3_direction_norm < EPSILON:
        return RayIntersection2(
            parallel=True,
            closest_point_1=ray_1.source_point,
            closest_point_2=ray_2.source_point)

    # system of equations Ax = b
    b = numpy.subtract(ray_2.source_point, ray_1.source_point)
    a = numpy.array(
        [ray_1_direction_normalized, -ray_2_direction_normalized, ray_3_direction], dtype="float32").transpose()
    x = numpy.linalg.solve(a, b)

    param_ray_1 = float(x[0])
    intersection_point_1 = ray_1.source_point + param_ray_1 * ray_1_direction_normalized

    param_ray_2 = float(x[1])
    intersection_point_2 = ray_2.source_point + param_ray_2 * ray_2_direction_normalized

    return RayIntersection2(
        parallel=False,
        closest_point_1=intersection_point_1,
        closest_point_2=intersection_point_2)


def closest_intersection_between_n_lines(
    rays: List[Ray],
    maximum_distance: float
) -> RayIntersectionN:
    ray_count = len(rays)
    intersections: List[RayIntersection2] = list()
    for ray_1_index in range(0, ray_count):
        for ray_2_index in range(ray_1_index + 1, ray_count):
            intersections.append(closest_intersection_between_two_lines(
                ray_1=rays[ray_1_index],
                ray_2=rays[ray_2_index]))
    centroids: List[numpy.array] = list()
    for intersection in intersections:
        if intersection.parallel:
            continue
        if intersection.distance() > maximum_distance:
            continue
        centroids.append(intersection.centroid())
    return RayIntersectionN(
        centroids=numpy.array(centroids, dtype="float32"),
        ray_count=ray_count)
