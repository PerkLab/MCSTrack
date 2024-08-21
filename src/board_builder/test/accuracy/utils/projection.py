# The math used is consistent with the OpenCV documentation: https://docs.opencv.org/4.x/d9/d0c/group__calib3d.html
import cv2
import numpy as np
from scipy.spatial.transform import Rotation
from src.common.structures import Matrix4x4, IntrinsicParameters


def projection(
    world_point,
    detector_to_reference_matrix: Matrix4x4,
    detector_intrinsics: IntrinsicParameters
) -> list[float]:
    """
    Projects 3D points onto the 2D detector frame
    """

    object_points: np.ndarray = np.asarray([world_point])
    reference_to_detector_matrix: Matrix4x4 = detector_to_reference_matrix.inverse()
    reference_to_detector_matrix_3x3: np.ndarray = reference_to_detector_matrix.as_numpy_array()[0:3, 0:3]
    rvec: np.ndarray = Rotation.from_matrix(reference_to_detector_matrix_3x3).as_rotvec(degrees=False)
    tvec: np.ndarray = np.asarray(reference_to_detector_matrix.get_translation())
    camera_matrix: np.ndarray = np.asarray(
        [[detector_intrinsics.focal_length_x_px, 0.0, detector_intrinsics.optical_center_x_px],
         [0.0, detector_intrinsics.focal_length_y_px, detector_intrinsics.optical_center_y_px],
         [0.0, 0.0, 1.0]])
    dist_coeffs: np.ndarray = np.asarray(detector_intrinsics.get_distortion_coefficients())
    image_points, _ = cv2.projectPoints(
        objectPoints=object_points,
        rvec=rvec,
        tvec=tvec,
        cameraMatrix=camera_matrix,
        distCoeffs=dist_coeffs)

    return [image_points[0][0][0], image_points[0][0][1]]

