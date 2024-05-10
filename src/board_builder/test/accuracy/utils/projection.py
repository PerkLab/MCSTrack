# The math used is consistent with the OpenCV documentation: https://docs.opencv.org/4.x/d9/d0c/group__calib3d.html
import numpy as np


def projection(world_point, camera_pos, camera_target, detector_intrinsics):
    """
    Projects 3D points onto the 2D detector frame
    """
    cx, cy = detector_intrinsics.optical_center_x_px, detector_intrinsics.optical_center_y_px

    # Camera coordinate system
    forward = camera_target - camera_pos
    forward = forward / np.linalg.norm(forward)
    up = np.array([0, 0, 1])
    right = np.cross(forward, up)
    up = np.cross(right, forward)

    # Convert world point to camera space
    point_relative = np.array(world_point) - camera_pos

    # Project point onto camera axes
    x = np.dot(point_relative, right)
    y = np.dot(point_relative, up)
    z = np.dot(point_relative, forward)

    # Check if the point is in front of the camera
    if z <= 0:
        return None  # Point is behind the camera

    # Project to image plane
    pixel_x = cx + detector_intrinsics.focal_length_x_px * x / z
    pixel_y = cy - detector_intrinsics.focal_length_y_px * y / z

    return [pixel_x, pixel_y]
