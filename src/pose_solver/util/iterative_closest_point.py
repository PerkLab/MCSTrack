# Algorithm is based on ICP: Besl and McKay. Method for registration of 3-D shapes. 1992.
import datetime  # for testing, not needed for the algorithm itself
import numpy
from scipy.spatial.transform import Rotation
from src.pose_solver.structures import Ray
from .closest_point_on_ray import closest_point_on_ray
from src.common.util import register_corresponding_points


class IterativeClosestPointParameters:
    # ICP will stop after this many iterations
    termination_iteration_count: int

    # ICP will stop if distance *and* angle difference from one iteration to the next
    # is smaller than these
    termination_delta_translation: float
    termination_delta_rotation_radians: float

    # ICP will stop if overall point-to-point distance (between source and target)
    # mean *or* root-mean-square is less than specified
    termination_mean_point_distance: float
    termination_rms_point_distance: float  # root-mean-square

    def __init__(
        self,
        termination_iteration_count: int,
        termination_delta_translation: float,
        termination_delta_rotation_radians: float,
        termination_mean_point_distance: float,
        termination_rms_point_distance: float
    ):
        self.termination_iteration_count = termination_iteration_count
        self.termination_delta_translation = termination_delta_translation
        self.termination_delta_rotation_radians = termination_delta_rotation_radians
        self.termination_mean_point_distance = termination_mean_point_distance
        self.termination_rms_point_distance = termination_rms_point_distance


class IterativeClosestPointOutput:
    source_to_target_matrix: numpy.ndarray
    iteration_count: int
    mean_point_distance: float
    rms_point_distance: float

    def __init__(
        self,
        source_to_target_matrix: numpy.ndarray,
        iteration_count: int,
        mean_point_distance: float,
        rms_point_distance: float
    ):
        self.source_to_target_matrix = source_to_target_matrix
        self.iteration_count = iteration_count
        self.mean_point_distance = mean_point_distance
        self.rms_point_distance = rms_point_distance


def _calculate_transformed_points(
    original_points: list[list[float]],
    transformation: numpy.ndarray
):
    transformed_points: list[list[float]] = list()
    for point in original_points:
        transformed_point = list(numpy.matmul(
            transformation,
            numpy.array([point[0], point[1], point[2], 1])))
        transformed_points.append([transformed_point[0], transformed_point[1], transformed_point[2]])
    return transformed_points


# This is a customized implementation for Iterative Closest Point
# adapted to the problem of registering a set of points to
# a set of points and rays where the correspondence is known.
def iterative_closest_point_for_points_and_rays(
    source_known_points: list[list[float]],
    target_known_points: list[list[float]],
    source_ray_points: list[list[float]],
    target_rays: list[Ray],
    parameters: IterativeClosestPointParameters = None,
    initial_transformation_matrix: numpy.ndarray = None
) -> IterativeClosestPointOutput:

    # Initial transformation
    source_to_transformed_matrix: numpy.ndarray
    if initial_transformation_matrix is not None:
        source_to_transformed_matrix = numpy.array(initial_transformation_matrix, dtype="float32")
    else:
        source_to_transformed_matrix = numpy.identity(4, dtype="float32")

    if parameters is None:
        parameters = IterativeClosestPointParameters(
            termination_iteration_count=50,
            termination_delta_translation=0.1,
            termination_delta_rotation_radians=0.001,
            termination_mean_point_distance=0.1,
            termination_rms_point_distance=0.1)

    transformed_known_points: list[list[float]] = _calculate_transformed_points(
        original_points=source_known_points,
        transformation=source_to_transformed_matrix)
    transformed_ray_points: list[list[float]] = _calculate_transformed_points(
        original_points=source_ray_points,
        transformation=source_to_transformed_matrix)

    iteration_count: int = 0
    mean_point_distance: float
    rms_point_distance: float
    while True:
        target_ray_points: list[list[float]] = list()
        for i, transformed_ray_point in enumerate(transformed_ray_points):
            target_ray_points.append(closest_point_on_ray(
                ray_source=target_rays[i].source_point,
                ray_direction=target_rays[i].direction,
                query_point=transformed_ray_point,
                forward_only=True))

        transformed_points = transformed_known_points + transformed_ray_points
        target_points = target_known_points + target_ray_points
        transformed_to_target_matrix = register_corresponding_points(
            point_set_from=transformed_points,
            point_set_to=target_points,
            collinearity_do_check=False)

        # update transformation & transformed points
        source_to_transformed_matrix = numpy.matmul(transformed_to_target_matrix, source_to_transformed_matrix)
        transformed_known_points: list[list[float]] = _calculate_transformed_points(
            original_points=source_known_points,
            transformation=source_to_transformed_matrix)
        transformed_ray_points: list[list[float]] = _calculate_transformed_points(
            original_points=source_ray_points,
            transformation=source_to_transformed_matrix)

        iteration_count += 1

        transformed_points = transformed_known_points + transformed_ray_points
        point_offsets = numpy.subtract(target_points, transformed_points).tolist()
        sum_point_distances = 0.0
        sum_square_point_distances = 0.0
        for delta_point_offset in point_offsets:
            delta_point_distance: float = numpy.linalg.norm(delta_point_offset)
            sum_point_distances += delta_point_distance
            sum_square_point_distances += numpy.square(delta_point_distance)
        mean_point_distance = sum_point_distances / len(point_offsets)
        rms_point_distance = numpy.sqrt(sum_square_point_distances / len(point_offsets))

        # Check if termination criteria are met
        # Note that transformed_to_target_matrix describes the change since last iteration, so we often operate on it
        delta_translation = numpy.linalg.norm(transformed_to_target_matrix[0:3, 3])
        delta_rotation_radians = \
            numpy.linalg.norm(Rotation.from_matrix(transformed_to_target_matrix[0:3, 0:3]).as_rotvec())
        if delta_translation < parameters.termination_delta_translation and \
           delta_rotation_radians < parameters.termination_delta_rotation_radians:
            break
        if mean_point_distance < parameters.termination_mean_point_distance:
            break
        if rms_point_distance < parameters.termination_rms_point_distance:
            break
        if iteration_count >= parameters.termination_iteration_count:
            break

    return IterativeClosestPointOutput(
        source_to_target_matrix=source_to_transformed_matrix,
        iteration_count=iteration_count,
        mean_point_distance=mean_point_distance,
        rms_point_distance=rms_point_distance)


def test():
    # Transformation is approximately
    source_known_points = [
        [2.0, 0.0, 2.0],
        [2.0, 2.0, 2.0],
        [2.0, 2.0, 0.0],
        [2.0, 0.0, 0.0]]
    source_ray_points = [
        [0.0, 2.0, 2.0],
        [0.0, 0.0, 2.0],
        [0.0, 0.0, 0.0],
        [0.0, 2.0, 0.0]]
    target_known_points = [
        [1.0, 1.0, -2.0],
        [-1.0, 1.0, -2.0],
        [-1.0, -1.0, -2.0],
        [1.0, -1.0, -2.0]]
    origin = [0.0, 0.0, 1.0]
    sqrt3 = numpy.sqrt(3.0)
    target_rays = [
        Ray(origin, [-sqrt3, sqrt3, -sqrt3]),
        Ray(origin, [sqrt3, sqrt3, -sqrt3]),
        Ray(origin, [sqrt3, -sqrt3, -sqrt3]),
        Ray(origin, [-sqrt3, -sqrt3, -sqrt3])]
    begin_datetime = datetime.datetime.utcnow()
    icp_parameters = IterativeClosestPointParameters(
        termination_iteration_count=100,
        termination_delta_translation=0.001,
        termination_delta_rotation_radians=0.001,
        termination_mean_point_distance=0.0001,
        termination_rms_point_distance=0.0001)
    icp_output = iterative_closest_point_for_points_and_rays(
        source_known_points=source_known_points,
        target_known_points=target_known_points,
        source_ray_points=source_ray_points,
        target_rays=target_rays,
        parameters=icp_parameters)
    source_to_target_matrix = icp_output.source_to_target_matrix
    end_datetime = datetime.datetime.utcnow()
    duration = (end_datetime - begin_datetime)
    duration_seconds = duration.seconds + (duration.microseconds / 1000000.0)
    message = str()
    for source_point in source_known_points:
        source_4d = [source_point[0], source_point[1], source_point[2], 1]
        target_4d = list(numpy.matmul(source_to_target_matrix, source_4d))
        target_point = [target_4d[0], target_4d[1], target_4d[2]]
        message = message + str(target_point) + "\n"
    message += "Algorithm took " + "{:.6f}".format(duration_seconds) + " seconds " + \
        "and took " + str(icp_output.iteration_count) + " iterations."
    print(message)


if __name__ == "__main__":
    test()
