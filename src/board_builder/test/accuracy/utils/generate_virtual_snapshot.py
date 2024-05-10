import numpy as np
from src.board_builder.test.accuracy.structures import AccuracyTestParameters


def generate_bounded_corners(board_definition, parameters):
    new_corners = {}
    for marker_id, corners in board_definition.items():
        new_corners[marker_id] = [
            [
                np.random.uniform(*parameters.SCENE_GENERATION_X_BOUNDS),
                np.random.uniform(*parameters.SCENE_GENERATION_Y_BOUNDS),
                np.random.uniform(*parameters.SCENE_GENERATION_Z_BOUNDS)
            ] for _ in corners
        ]
    return new_corners


def calculate_transform(original_corners, new_corners):
    # Compute centroids
    original_centroid = np.mean(original_corners, axis=0)
    new_centroid = np.mean(new_corners, axis=0)

    # Center the point sets
    centered_original = original_corners - original_centroid
    centered_new = new_corners - new_centroid

    # Compute the covariance matrix
    H = centered_original.T @ centered_new

    # Compute the rotation using SVD
    U, _, Vt = np.linalg.svd(H)
    R = Vt.T @ U.T

    # Ensure it's a proper rotation matrix (det(R) = 1)
    if np.linalg.det(R) < 0:
        Vt[-1, :] *= -1
        R = Vt.T @ U.T

    # Limit the rotation
    angle_limit = np.deg2rad(AccuracyTestParameters.SCENE_GENERATION_ROTATION_LIMIT)
    axis, angle = rotation_matrix_to_axis_angle(R)
    if angle > angle_limit:
        angle = angle_limit
    R = axis_angle_to_rotation_matrix(axis, angle)

    # Compute the translation
    t = new_centroid - R @ original_centroid

    # Construct the 4x4 transformation matrix
    transform = np.eye(4)
    transform[:3, :3] = R
    transform[:3, 3] = t

    return transform


def rotation_matrix_to_axis_angle(R):
    angle = np.arccos((np.trace(R) - 1) / 2)
    if angle == 0:
        return np.array([1, 0, 0]), 0
    rx = R[2, 1] - R[1, 2]
    ry = R[0, 2] - R[2, 0]
    rz = R[1, 0] - R[0, 1]
    axis = np.array([rx, ry, rz])
    axis = axis / np.linalg.norm(axis)
    return axis, angle


def axis_angle_to_rotation_matrix(axis, angle):
    K = np.array([
        [0, -axis[2], axis[1]],
        [axis[2], 0, -axis[0]],
        [-axis[1], axis[0], 0]
    ])
    I = np.eye(3)
    R = I + np.sin(angle) * K + (1 - np.cos(angle)) * K @ K
    return R


def apply_transform(board_definition, parameters):
    new_corners = generate_bounded_corners(board_definition, parameters)

    # Use the first marker to calculate the transformation
    marker_id = list(board_definition.keys())[0]
    original_corners = np.array(board_definition[marker_id])
    transform = calculate_transform(original_corners, np.array(new_corners[marker_id]))

    transformed_board = {}
    for marker_id, corners in board_definition.items():
        transformed_corners = []
        for corner in corners:
            # Convert to homogeneous coordinates
            point = np.array(corner + [1])
            # Apply transformation
            transformed_point = transform @ point
            # Convert back to 3D coordinates
            transformed_corners.append(transformed_point[:3].tolist())
        transformed_board[marker_id] = transformed_corners
    return transformed_board


def generate_virtual_snapshots(board_definition, count):
    """
    Given a board definition, generate X more scenes of that board with random rotation and translation within bounds
    """
    parameters = AccuracyTestParameters()
    snapshots = []
    for _ in range(count):
        transformed_board = apply_transform(board_definition, parameters)
        snapshots.append(transformed_board)
    return snapshots
