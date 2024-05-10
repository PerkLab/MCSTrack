from src.pose_solver.pose_solver import PoseSolver
from src.common.structures import \
    IntrinsicParameters, \
    Matrix4x4, \
    Pose
from src.pose_solver.structures import \
    MarkerCorners, \
    TargetMarker
import datetime
from typing import Final
import unittest


REFERENCE_MARKER_ID: Final[int] = 0
TARGET_MARKER_ID: Final[int] = 1
MARKER_SIZE_MM: Final[float] = 10.0
DETECTOR_RED_NAME: Final[str] = "det_red"
DETECTOR_RED_INTRINSICS: Final[IntrinsicParameters] = IntrinsicParameters(
    focal_length_x_px=639.868693422552,
    focal_length_y_px=641.6791698765336,
    optical_center_x_px=323.14153105889875,
    optical_center_y_px=220.61329828934248,
    radial_distortion_coefficients=[
        0.08666240819049885,
        -0.2774881204787844,
        0.7597374427695651],
    tangential_distortion_coefficients=[
        0.002222924678874641,
        0.000451202639540722])
DETECTOR_SKY_NAME: Final[str] = "det_sky"
DETECTOR_SKY_INTRINSICS = IntrinsicParameters(
    focal_length_x_px=634.5571762295385,
    focal_length_y_px=635.8752665544757,
    optical_center_x_px=342.2796848405297,
    optical_center_y_px=237.25876152611903,
    radial_distortion_coefficients=[
        0.007893260347873363,
        0.4039379816012414,
        -1.310328007486472],
    tangential_distortion_coefficients=[
        -0.00427611562879615,
        0.0011943327833114237])
DETECTOR_GREEN_NAME: Final[str] = "det_green"
DETECTOR_GREEN_INTRINSICS: Final[IntrinsicParameters] = IntrinsicParameters(
    focal_length_x_px=629.7257712407858,
    focal_length_y_px=631.1144336572407,
    optical_center_x_px=327.78473901724755,
    optical_center_y_px=226.74054836282653,
    radial_distortion_coefficients=[
        0.05560270909494751,
        -0.28733139601291297,
        1.182627063988894],
    tangential_distortion_coefficients=[
        -0.00454124371092251,
        0.0009635939551320261])
DETECTOR_YELLOW_NAME: Final[str] = "det_yellow"
DETECTOR_YELLOW_INTRINSICS: Final[IntrinsicParameters] = IntrinsicParameters(
    focal_length_x_px=631.8473035705026,
    focal_length_y_px=633.1359456295344,
    optical_center_x_px=320.2359771205735,
    optical_center_y_px=229.907674657082,
    radial_distortion_coefficients=[
        0.02632957785166054,
        0.08738574865741917,
        -0.08927215783058062],
    tangential_distortion_coefficients=[
        -0.0032460684079051905,
        0.0022403564492654584])


class TestPoseSolver(unittest.TestCase):

    def assertRotationCloseToIdentity(
        self,
        matrix: Matrix4x4,
        tolerance: float = 0.1
    ) -> None:
        self.assertAlmostEqual(matrix[0, 0], 1.0, delta=tolerance)
        self.assertAlmostEqual(matrix[0, 1], 0.0, delta=tolerance)
        self.assertAlmostEqual(matrix[0, 2], 0.0, delta=tolerance)
        self.assertAlmostEqual(matrix[1, 0], 0.0, delta=tolerance)
        self.assertAlmostEqual(matrix[1, 1], 1.0, delta=tolerance)
        self.assertAlmostEqual(matrix[1, 2], 0.0, delta=tolerance)
        self.assertAlmostEqual(matrix[2, 0], 0.0, delta=tolerance)
        self.assertAlmostEqual(matrix[2, 1], 0.0, delta=tolerance)
        self.assertAlmostEqual(matrix[2, 2], 1.0, delta=tolerance)

    def test_single_camera_viewing_target_marker(self):
        # Note that single-marker tests are particularly susceptible to reference pose ambiguity
        now_utc = datetime.datetime.utcnow()
        pose_solver: PoseSolver = PoseSolver()
        pose_solver.set_intrinsic_parameters(
            detector_label=DETECTOR_RED_NAME,
            intrinsic_parameters=DETECTOR_RED_INTRINSICS)
        pose_solver.set_reference_target(
            target=TargetMarker(
                marker_id=REFERENCE_MARKER_ID,
                marker_size=MARKER_SIZE_MM))
        pose_solver.add_target_marker(
            marker_id=TARGET_MARKER_ID,
            marker_diameter=MARKER_SIZE_MM)
        # Reference is on the left, target is on the right, both in the same plane and along the x-axis of the image.
        pose_solver.add_marker_corners(
            detected_corners=[
                MarkerCorners(
                    detector_label=DETECTOR_RED_NAME,
                    marker_id=REFERENCE_MARKER_ID,
                    points=[
                        [375, 347],
                        [415, 346],
                        [416, 386],
                        [376, 386]],
                    timestamp=now_utc),
                MarkerCorners(
                    detector_label=DETECTOR_RED_NAME,
                    marker_id=TARGET_MARKER_ID,
                    points=[
                        [541, 347],
                        [581, 348],
                        [580, 388],
                        [540, 387]],
                    timestamp=now_utc)])
        pose_solver.update()
        detector_poses: list[Pose]
        target_poses: list[Pose]
        detector_poses, target_poses = pose_solver.get_poses()

        self.assertEqual(len(detector_poses), 1)
        # Relative to the reference, detector is primarily shifted in positive direction along z-axis.
        matrix: Matrix4x4 = detector_poses[0].object_to_reference_matrix
        self.assertGreater(matrix[2, 3], 0.0)
        self.assertGreater(abs(matrix[2, 3]), abs(matrix[0, 3]))
        self.assertGreater(abs(matrix[2, 3]), abs(matrix[1, 3]))
        # Last row should be 0's and 1
        self.assertEqual(matrix[3, 0], 0.0)
        self.assertEqual(matrix[3, 1], 0.0)
        self.assertEqual(matrix[3, 2], 0.0)
        self.assertEqual(matrix[3, 3], 1.0)

        self.assertEqual(len(target_poses), 1)
        # Relative to the reference, target is primarily shifted in positive direction along x-axis.
        matrix: Matrix4x4 = target_poses[0].object_to_reference_matrix
        self.assertGreater(matrix[0, 3], 0.0)
        self.assertGreater(abs(matrix[0, 3]), abs(matrix[1, 3]))
        self.assertGreater(abs(matrix[0, 3]), abs(matrix[2, 3]))
        # Verify rotation is close to identity (very little rotation)
        self.assertRotationCloseToIdentity(matrix=matrix)
        # Last row should be 0's and 1
        self.assertEqual(matrix[3, 0], 0.0)
        self.assertEqual(matrix[3, 1], 0.0)
        self.assertEqual(matrix[3, 2], 0.0)
        self.assertEqual(matrix[3, 3], 1.0)

    def test_four_cameras_viewing_target_marker(self):
        # Note that single-marker tests are particularly susceptible to reference pose ambiguity
        now_utc = datetime.datetime.utcnow()
        pose_solver: PoseSolver = PoseSolver()
        pose_solver.set_intrinsic_parameters(
            detector_label=DETECTOR_RED_NAME,
            intrinsic_parameters=DETECTOR_RED_INTRINSICS)
        pose_solver.set_intrinsic_parameters(
            detector_label=DETECTOR_SKY_NAME,
            intrinsic_parameters=DETECTOR_SKY_INTRINSICS)
        pose_solver.set_intrinsic_parameters(
            detector_label=DETECTOR_GREEN_NAME,
            intrinsic_parameters=DETECTOR_GREEN_INTRINSICS)
        pose_solver.set_intrinsic_parameters(
            detector_label=DETECTOR_YELLOW_NAME,
            intrinsic_parameters=DETECTOR_YELLOW_INTRINSICS)
        pose_solver.set_reference_target(
            target=TargetMarker(
                marker_id=REFERENCE_MARKER_ID,
                marker_size=MARKER_SIZE_MM))
        pose_solver.add_target_marker(
            marker_id=TARGET_MARKER_ID,
            marker_diameter=MARKER_SIZE_MM)
        pose_solver.add_marker_corners(
            detected_corners=[
                MarkerCorners(
                    detector_label=DETECTOR_RED_NAME,
                    marker_id=REFERENCE_MARKER_ID,
                    points=[
                        [157, 210],
                        [165, 221],
                        [139, 229],
                        [131, 217]],
                    timestamp=now_utc),
                MarkerCorners(
                    detector_label=DETECTOR_RED_NAME,
                    marker_id=TARGET_MARKER_ID,
                    points=[
                        [196, 266],
                        [206, 281],
                        [178, 291],
                        [167, 275]],
                    timestamp=now_utc),
                MarkerCorners(
                    detector_label=DETECTOR_SKY_NAME,
                    marker_id=REFERENCE_MARKER_ID,
                    points=[
                        [190, 234],
                        [219, 246],
                        [195, 270],
                        [166, 257]],
                    timestamp=now_utc),
                MarkerCorners(
                    detector_label=DETECTOR_SKY_NAME,
                    marker_id=TARGET_MARKER_ID,
                    points=[
                        [317, 290],
                        [352, 306],
                        [332, 333],
                        [296, 317]],
                    timestamp=now_utc),
                MarkerCorners(
                    detector_label=DETECTOR_GREEN_NAME,
                    marker_id=REFERENCE_MARKER_ID,
                    points=[
                        [247, 304],
                        [283, 296],
                        [291, 326],
                        [254, 334]],
                    timestamp=now_utc),
                MarkerCorners(
                    detector_label=DETECTOR_GREEN_NAME,
                    marker_id=TARGET_MARKER_ID,
                    points=[
                        [392, 277],
                        [426, 271],
                        [438, 299],
                        [403, 305]],
                    timestamp=now_utc),
                MarkerCorners(
                    detector_label=DETECTOR_YELLOW_NAME,
                    marker_id=REFERENCE_MARKER_ID,
                    points=[
                        [275, 277],
                        [289, 251],
                        [321, 261],
                        [306, 288]],
                    timestamp=now_utc),
                MarkerCorners(
                    detector_label=DETECTOR_YELLOW_NAME,
                    marker_id=TARGET_MARKER_ID,
                    points=[
                        [332, 177],
                        [344, 156],
                        [372, 163],
                        [361, 185]],
                    timestamp=now_utc)])
        pose_solver.update()
        detector_poses: list[Pose]
        target_poses: list[Pose]
        detector_poses, target_poses = pose_solver.get_poses()

        self.assertEqual(len(detector_poses), 4)
        # Relative to the reference, all detectors are shifted in positive direction along z-axis.
        for detector_index in range(0, 4):
            matrix: Matrix4x4 = detector_poses[detector_index].object_to_reference_matrix
            self.assertGreater(matrix[2, 3], 0.0)

        self.assertEqual(len(target_poses), 1)
        # Relative to the reference, target is primarily shifted in positive direction along x-axis.
        matrix: Matrix4x4 = target_poses[0].object_to_reference_matrix
        self.assertAlmostEqual(matrix[0, 3], 40.0, delta=2.5)
        self.assertAlmostEqual(matrix[1, 3], 0.0, delta=2.5)
        self.assertAlmostEqual(matrix[2, 3], 0.0, delta=2.5)
        self.assertRotationCloseToIdentity(matrix=matrix)
        # Last row should be 0's and 1
        self.assertEqual(matrix[3, 0], 0.0)
        self.assertEqual(matrix[3, 1], 0.0)
        self.assertEqual(matrix[3, 2], 0.0)
        self.assertEqual(matrix[3, 3], 1.0)
        self.assertEqual(matrix[3, 3], 1.0)
