from src.pose_solver.pose_solver import PoseSolver
from src.common.structures import \
    DetectorFrame, \
    IntrinsicParameters, \
    MarkerCornerImagePoint, \
    MarkerSnapshot, \
    Matrix4x4, \
    Pose, \
    MarkerCorners
from src.pose_solver.structures import \
    TargetMarker
import datetime
from typing import Final
import unittest


MARKER_SIZE_MM: Final[float] = 10.0
REFERENCE_TARGET_ID: Final[str] = "reference"
REFERENCE_MARKER_ID: Final[str] = "0"
REFERENCE_MARKER_TARGET: Final[TargetMarker] = TargetMarker(
    target_id=REFERENCE_TARGET_ID,
    marker_id=REFERENCE_MARKER_ID,
    marker_size=MARKER_SIZE_MM)
TARGET_TARGET_ID: Final[str] = "target"
TARGET_MARKER_ID: Final[str] = "1"
TARGET_MARKER_TARGET: Final[TargetMarker] = TargetMarker(
    target_id=TARGET_TARGET_ID,
    marker_id=TARGET_MARKER_ID,
    marker_size=MARKER_SIZE_MM)
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
        pose_solver.add_target(target=REFERENCE_MARKER_TARGET)
        pose_solver.add_target(target=TARGET_MARKER_TARGET)
        pose_solver.set_reference_target(target_id=REFERENCE_MARKER_TARGET.target_id)
        # Reference is on the left, target is on the right, both in the same plane and along the x-axis of the image.
        pose_solver.add_detector_frame(
            detector_label=DETECTOR_RED_NAME,
            detector_frame=DetectorFrame(
                detected_marker_snapshots=[
                    MarkerSnapshot(
                        label=str(REFERENCE_MARKER_ID),
                        corner_image_points=[
                            MarkerCornerImagePoint(x_px=375, y_px=347),
                            MarkerCornerImagePoint(x_px=415, y_px=346),
                            MarkerCornerImagePoint(x_px=416, y_px=386),
                            MarkerCornerImagePoint(x_px=376, y_px=386)]),
                    MarkerSnapshot(
                        label=str(TARGET_MARKER_ID),
                        corner_image_points=[
                            MarkerCornerImagePoint(x_px=541, y_px=347),
                            MarkerCornerImagePoint(x_px=581, y_px=348),
                            MarkerCornerImagePoint(x_px=580, y_px=388),
                            MarkerCornerImagePoint(x_px=540, y_px=387)])],
                rejected_marker_snapshots=list(),
                timestamp_utc_iso8601=now_utc.isoformat()))
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
        pose_solver.add_target(target=REFERENCE_MARKER_TARGET)
        pose_solver.add_target(target=TARGET_MARKER_TARGET)
        pose_solver.set_reference_target(target_id=REFERENCE_MARKER_TARGET.target_id)
        pose_solver.add_detector_frame(
            detector_label=DETECTOR_RED_NAME,
            detector_frame=DetectorFrame(
                detected_marker_snapshots=[
                    MarkerSnapshot(
                        label=str(REFERENCE_MARKER_ID),
                        corner_image_points=[
                            MarkerCornerImagePoint(x_px=157, y_px=210),
                            MarkerCornerImagePoint(x_px=165, y_px=221),
                            MarkerCornerImagePoint(x_px=139, y_px=229),
                            MarkerCornerImagePoint(x_px=131, y_px=217)]),
                    MarkerSnapshot(
                        label=str(TARGET_MARKER_ID),
                        corner_image_points=[
                            MarkerCornerImagePoint(x_px=196, y_px=266),
                            MarkerCornerImagePoint(x_px=206, y_px=281),
                            MarkerCornerImagePoint(x_px=178, y_px=291),
                            MarkerCornerImagePoint(x_px=167, y_px=275)])],
                rejected_marker_snapshots=list(),
                timestamp_utc_iso8601=now_utc.isoformat()))
        pose_solver.add_detector_frame(
            detector_label=DETECTOR_SKY_NAME,
            detector_frame=DetectorFrame(
                detected_marker_snapshots=[
                    MarkerSnapshot(
                        label=str(REFERENCE_MARKER_ID),
                        corner_image_points=[
                            MarkerCornerImagePoint(x_px=190, y_px=234),
                            MarkerCornerImagePoint(x_px=219, y_px=246),
                            MarkerCornerImagePoint(x_px=195, y_px=270),
                            MarkerCornerImagePoint(x_px=166, y_px=257)]),
                    MarkerSnapshot(
                        label=str(TARGET_MARKER_ID),
                        corner_image_points=[
                            MarkerCornerImagePoint(x_px=317, y_px=290),
                            MarkerCornerImagePoint(x_px=352, y_px=306),
                            MarkerCornerImagePoint(x_px=332, y_px=333),
                            MarkerCornerImagePoint(x_px=296, y_px=317)])],
                rejected_marker_snapshots=list(),
                timestamp_utc_iso8601=now_utc.isoformat()))
        pose_solver.add_detector_frame(
            detector_label=DETECTOR_GREEN_NAME,
            detector_frame=DetectorFrame(
                detected_marker_snapshots=[
                    MarkerSnapshot(
                        label=str(REFERENCE_MARKER_ID),
                        corner_image_points=[
                            MarkerCornerImagePoint(x_px=247, y_px=304),
                            MarkerCornerImagePoint(x_px=283, y_px=296),
                            MarkerCornerImagePoint(x_px=291, y_px=326),
                            MarkerCornerImagePoint(x_px=254, y_px=334)]),
                    MarkerSnapshot(
                        label=str(TARGET_MARKER_ID),
                        corner_image_points=[
                            MarkerCornerImagePoint(x_px=392, y_px=277),
                            MarkerCornerImagePoint(x_px=426, y_px=271),
                            MarkerCornerImagePoint(x_px=438, y_px=299),
                            MarkerCornerImagePoint(x_px=403, y_px=305)])],
                rejected_marker_snapshots=list(),
                timestamp_utc_iso8601=now_utc.isoformat()))
        pose_solver.add_detector_frame(
            detector_label=DETECTOR_YELLOW_NAME,
            detector_frame=DetectorFrame(
                detected_marker_snapshots=[
                    MarkerSnapshot(
                        label=str(REFERENCE_MARKER_ID),
                        corner_image_points=[
                            MarkerCornerImagePoint(x_px=275, y_px=277),
                            MarkerCornerImagePoint(x_px=289, y_px=251),
                            MarkerCornerImagePoint(x_px=321, y_px=261),
                            MarkerCornerImagePoint(x_px=306, y_px=288)]),
                    MarkerSnapshot(
                        label=str(TARGET_MARKER_ID),
                        corner_image_points=[
                            MarkerCornerImagePoint(x_px=332, y_px=177),
                            MarkerCornerImagePoint(x_px=344, y_px=156),
                            MarkerCornerImagePoint(x_px=372, y_px=163),
                            MarkerCornerImagePoint(x_px=361, y_px=185)])],
                rejected_marker_snapshots=list(),
                timestamp_utc_iso8601=now_utc.isoformat()))
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
