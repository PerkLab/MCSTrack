import math
import random
import numpy as np
from src.board_builder.test.accuracy.structures import AccuracyTestParameters
from .projection import projection
from collections import defaultdict

from src.common.structures import MarkerSnapshot, MarkerCornerImagePoint


def find_z_axis_intersection(matrix4x4):
    transform_matrix = matrix4x4.as_numpy_array()

    # Extract rotation matrix (3x3) and translation vector (3x1)
    rotation_matrix = transform_matrix[:3, :3]
    translation_vector = transform_matrix[:3, 3]

    # The z-axis direction in world coordinates is the third column of the rotation matrix
    z_axis_direction = rotation_matrix[:, 2]

    # Camera position is the translation vector
    camera_position = translation_vector

    # Parametric equation of the line: point = camera_position + t * z_axis_direction
    # We need to find t where the z-component becomes 0

    # Solve for t: camera_position[2] + t * z_axis_direction[2] = 0
    t = -camera_position[2] / z_axis_direction[2]

    # Calculate the intersection point
    intersection_point = camera_position + t * z_axis_direction

    return intersection_point

def is_square_normal_pointing_away_from_detector(marker_corners, detector_pose, tolerance):
    """
    Check if a marker's normal is perpendicular or pointing away from the detector in which case it will be occluded
    """

    def calculate_normal(corners):
        # Compute vectors from the given corners
        v1 = np.array(corners[1], dtype=np.float64) - np.array(corners[0], dtype=np.float64)
        v2 = np.array(corners[3], dtype=np.float64) - np.array(corners[0], dtype=np.float64)

        # Calculate the normal vector using the cross product
        normal = np.cross(v1, v2)
        # Normalize the normal vector
        normal /= np.linalg.norm(normal)

        return - normal

    def calculate_center(corners):
        # Calculate the center of the square
        center = np.mean(corners, axis=0)
        return center

    transform_matrix = detector_pose.object_to_reference_matrix.as_numpy_array()
    detector_position = transform_matrix[:3, 3]  # The position of the detector

    normal = calculate_normal(marker_corners)
    center = calculate_center(marker_corners)
    detector_to_center_vec = center - detector_position

    # Normalize the vectors
    normal = normal / np.linalg.norm(normal)
    detector_to_center_vec = detector_to_center_vec / np.linalg.norm(detector_to_center_vec)

    # Check if the normal is pointing away
    dot_product = np.dot(normal, detector_to_center_vec)
    return dot_product >= tolerance


def generate_data(board_coordinates, detector_poses, remove_markers_out_of_frame=False):
    """
    Given board data in 3D space, convert that data into a format that can be passed to board builder
    Also trims the data to remove any occluded marker
    """
    parameters = AccuracyTestParameters()
    collection_data: dict[str, list[MarkerSnapshot]] = {}
    occluded_markers = defaultdict(list, {pose.target_id: [] for pose in detector_poses})  # A list of markers that are occluded (self occlusion or perpendicular)

    # Collect data
    for pose in detector_poses:
        marker_snapshot_list = []
        transform_matrix = pose.object_to_reference_matrix.as_numpy_array()
        camera_pos = transform_matrix[:3, 3]
        intersection = find_z_axis_intersection(pose.object_to_reference_matrix)

        for marker in board_coordinates:

            # Check if perpendicular
            if marker in occluded_markers[pose.target_id]:
                break

            marker_corners = []
            for corner in board_coordinates[marker]:
                pixel = projection(corner, camera_pos, intersection, parameters.DETECTOR_INTRINSICS)
                # Check if marker out of frame
                if remove_markers_out_of_frame and (not pixel or not (0 < pixel[0] < parameters.DETECTOR_FRAME_WIDTH) or not (0 < pixel[1] < parameters.DETECTOR_FRAME_HEIGHT)):
                    break
                if pixel is not None:
                    marker_corners.append(pixel)

            if len(marker_corners) == 4:
                marker_snapshot = MarkerSnapshot(label=str(marker), corner_image_points=[])
                marker_snapshot.label = str(marker)
                marker_corner_image_point_list = []
                for marker_corner in marker_corners:
                    marker_corner_image_point = MarkerCornerImagePoint(x_px=marker_corner[0], y_px=marker_corner[1])
                    marker_corner_image_point_list.append(marker_corner_image_point)
                marker_snapshot_list.append(MarkerSnapshot(label=str(marker), corner_image_points=marker_corner_image_point_list))

        collection_data[pose.target_id] = marker_snapshot_list

    return collection_data


