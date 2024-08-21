# Solution based on: Arun et al. Least square fitting of two 3D point sets (1987)
# https://stackoverflow.com/questions/66923224/rigid-registration-of-two-point-clouds-with-known-correspondence
# Use mirroring solution proposed by Oomori et al.
# Oomori et al. Point cloud matching using singular value decomposition. (2016)
import numpy


def register_corresponding_points(
    point_set_from: list[list[float]],
    point_set_to: list[list[float]],
    collinearity_do_check: bool = True,
    collinearity_zero_threshold: float = 0.0001,
    use_oomori_mirror_fix: bool = True
) -> numpy.array:  # 4x4 transformation matrix, indexed by [row,col]
    """
    :param point_set_from:
    :param point_set_to:
    :param collinearity_do_check: Do a (naive) collinearity check. May be computationally expensive.
    :param collinearity_zero_threshold: Threshold considered zero for cross product and norm comparisons
    """
    if len(point_set_from) != len(point_set_to):
        raise ValueError("Input point sets must be of identical length.")
    if len(point_set_from) < 3:
        raise ValueError("Input point sets must be of length 3 or higher.")
    if collinearity_do_check:
        for point_set in (point_set_from, point_set_to):
            collinear = True  # assume true until shown otherwise
            p1: numpy.ndarray = numpy.asarray(point_set[0])
            vec1: numpy.ndarray
            i: int = 1
            for i in range(i, len(point_set)):
                p2: numpy.ndarray = numpy.asarray(point_set[1])
                vec1 = p2 - p1
                vec1_length: float = numpy.linalg.norm(vec1)
                if vec1_length > collinearity_zero_threshold:
                    break  # points are distinct, move to next phase
            for i in range(i, len(point_set)):
                p3: numpy.ndarray = numpy.asarray(point_set[2])
                vec2: numpy.ndarray = p3 - p1
                cross_product_norm: float = numpy.linalg.norm(numpy.cross(vec1, vec2))
                if cross_product_norm > collinearity_zero_threshold:
                    collinear = False
                    break
            if collinear:
                raise ValueError("Input points appear to be collinear - please check the input.")

    # for consistency, points are in rows
    point_count = len(point_set_from)
    sums_from = numpy.array([0, 0, 0], dtype="float32")
    sums_to = numpy.array([0, 0, 0], dtype="float32")
    for point_index in range(0, point_count):
        sums_from += numpy.array(point_set_from[point_index])
        sums_to += numpy.array(point_set_to[point_index])
    centroid_from = (sums_from / point_count)
    centroid_to = (sums_to / point_count)
    points_from = numpy.array(point_set_from)
    points_to = numpy.array(point_set_to)
    centered_points_from = points_from - numpy.hstack(centroid_from)
    centered_points_to = points_to - numpy.hstack(centroid_to)
    covariance = numpy.matmul(centered_points_from.T, centered_points_to)
    u, _, vh = numpy.linalg.svd(covariance)
    s = numpy.identity(3, dtype="float32")  # s will be the Oomori mirror fix
    if use_oomori_mirror_fix:
        s[2, 2] = numpy.linalg.det(numpy.matmul(u, vh))
    rotation = numpy.matmul(u, numpy.matmul(s, vh)).transpose()
    translation = centroid_to - numpy.matmul(rotation, centroid_from)
    matrix = numpy.identity(4, dtype="float32")
    matrix[0:3, 0:3] = rotation
    matrix[0:3, 3] = translation[0:3].reshape(3)
    return matrix
