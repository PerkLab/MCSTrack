from .exceptions import \
    PoseSolverException
from .structures import \
    DetectorRecord, \
    DetectorFrameRecord, \
    Ray, \
    PoseSolverParameters
from .util import \
    average_quaternion, \
    average_vector, \
    closest_intersection_between_n_lines, \
    IterativeClosestPointParameters, \
    iterative_closest_point_for_points_and_rays, \
    register_corresponding_points
from src.common.structures import \
    DetectorFrame, \
    IntrinsicParameters, \
    Matrix4x4, \
    Pose, \
    TargetBase
from src.common.util import \
    MathUtils
import cv2
import cv2.aruco
import datetime
import itertools
import numpy
from scipy.spatial.transform import Rotation
from typing import Final, TypeVar


EPSILON: Final[float] = 0.0001
_CORNER_COUNT: Final[int] = 4

KeyType = TypeVar("KeyType")
ValueType = TypeVar("ValueType")


class PoseSolver:
    """
    Class containing the actual "solver" logic, kept separate from the API.
    """

    # bookkeeping
    _last_change_timestamp_utc: datetime.datetime
    _last_updated_timestamp_utc: datetime.datetime

    # inputs
    _parameters: PoseSolverParameters
    _intrinsics_by_detector_label: dict[str, IntrinsicParameters]
    _extrinsics_by_detector_label: dict[str, Matrix4x4]
    _targets: list[TargetBase]  # First target is considered the "reference"
    # input per frame
    _detector_records_by_detector_label: dict[str, DetectorRecord]

    # internal threshold
    _minimum_marker_age_before_removal_seconds: float
    # use this to make sure each marker is associated uniquely to a single target
    _marker_target_map: dict[str, TargetBase]  # Each marker shall be used at most once by a single target

    # outputs
    _poses_by_target_id: dict[str, Matrix4x4]
    _poses_by_detector_label: dict[str, Matrix4x4]

    def __init__(
        self
    ):
        self._last_change_timestamp_utc = datetime.datetime.min
        self._last_updated_timestamp_utc = datetime.datetime.min

        self._parameters = PoseSolverParameters()
        self._intrinsics_by_detector_label = dict()
        self._extrinsics_by_detector_label = dict()
        self._targets = list()
        self._detector_records_by_detector_label = dict()

        self._minimum_marker_age_before_removal_seconds = max([
            self._parameters.POSE_DETECTOR_DENOISE_LIMIT_AGE_SECONDS,
            self._parameters.POSE_SINGLE_CAMERA_EXTRAPOLATION_LIMIT_RAY_AGE_SECONDS,
            self._parameters.POSE_SINGLE_CAMERA_NEAREST_LIMIT_RAY_AGE_SECONDS,
            self._parameters.POSE_SINGLE_CAMERA_DEPTH_LIMIT_AGE_SECONDS,
            self._parameters.POSE_MULTI_CAMERA_LIMIT_RAY_AGE_SECONDS])
        self._marker_target_map = dict()

        self._poses_by_target_id = dict()
        self._poses_by_detector_label = dict()

    def add_detector_frame(
        self,
        detector_label: str,
        detector_frame: DetectorFrame
    ) -> None:
        detector_frame_record: DetectorFrameRecord = DetectorFrameRecord(
            detector_label=detector_label,
            frame=detector_frame)
        if detector_label not in self._detector_records_by_detector_label:
            self._detector_records_by_detector_label[detector_label] = DetectorRecord()
        self._detector_records_by_detector_label[detector_label].clear_frame_records()
        self._detector_records_by_detector_label[detector_label].add_frame_record(detector_frame_record)
        self._last_change_timestamp_utc = datetime.datetime.utcnow()

    def add_target(
        self,
        target: TargetBase
    ) -> None:
        for existing_target in self._targets:
            if target.target_id == existing_target.target_id:
                raise PoseSolverException(
                    f"Target with name {target.target_id} is already registered. "
                    f"Please use a different name, and also make sure you are not adding the same target twice.")
        marker_ids = target.get_marker_ids()
        for marker_id in marker_ids:
            if marker_id in self._marker_target_map:
                target_id: str = self._marker_target_map[marker_id].target_id
                raise PoseSolverException(
                    f"Marker {marker_id} is already used with target {target_id} and it cannot be reused.")
        target_index = len(self._targets)
        self._targets.append(target)
        for marker_id in marker_ids:
            self._marker_target_map[marker_id] = self._targets[target_index]
        self._last_change_timestamp_utc = datetime.datetime.utcnow()

    def clear_extrinsic_matrices(self):
        self._extrinsics_by_detector_label.clear()
        self._last_change_timestamp_utc = datetime.datetime.utcnow()

    def clear_intrinsic_parameters(self):
        self._intrinsics_by_detector_label.clear()
        self._last_change_timestamp_utc = datetime.datetime.utcnow()

    def clear_targets(self):
        self._targets.clear()
        self._marker_target_map.clear()
        self._last_change_timestamp_utc = datetime.datetime.utcnow()

    def get_poses(
        self
    ) -> tuple[list[Pose], list[Pose]]:
        """
        Returns detector_poses, target_poses
        """
        detector_poses: list[Pose] = [
            Pose(
                target_id=detector_label,
                object_to_reference_matrix=pose,
                solver_timestamp_utc_iso8601=self._last_updated_timestamp_utc.isoformat())
            for detector_label, pose in self._poses_by_detector_label.items()]
        target_poses: list[Pose] = [
            Pose(
                target_id=str(target_id),
                object_to_reference_matrix=pose,
                solver_timestamp_utc_iso8601=self._last_updated_timestamp_utc.isoformat())
            for target_id, pose in self._poses_by_target_id.items()]
        return detector_poses, target_poses

    def list_targets(self) -> list[TargetBase]:
        return self._targets

    def set_extrinsic_matrix(
        self,
        detector_label: str,
        transform_to_reference: Matrix4x4
    ) -> None:
        self._extrinsics_by_detector_label[detector_label] = transform_to_reference
        self._last_change_timestamp_utc = datetime.datetime.utcnow()

    def set_intrinsic_parameters(
        self,
        detector_label: str,
        intrinsic_parameters: IntrinsicParameters
    ) -> None:
        self._intrinsics_by_detector_label[detector_label] = intrinsic_parameters
        self._last_change_timestamp_utc = datetime.datetime.utcnow()

    def set_reference_target(
        self,
        target_id: str
    ) -> None:
        found: bool = False
        for target_index, target in enumerate(self._targets):
            if target.target_id == target_id:
                self._targets[0], self._targets[target_index] = self._targets[target_index], self._targets[0]
                self._last_change_timestamp_utc = datetime.datetime.utcnow()
                found = True
                break
        if not found:
            raise PoseSolverException(f"{target_id} was not found.")

    def set_targets(
        self,
        targets: list[TargetBase]
    ) -> None:
        self._targets = targets
        self._poses_by_target_id.clear()
        self._poses_by_detector_label.clear()
        self._last_change_timestamp_utc = datetime.datetime.utcnow()

    def _calculate_reprojection_error_for_pose(
        self,
        ray_set: ...,
        object_points_target: list[list[float]],
        object_to_reference_translation: list[float],
        object_to_reference_rotation_quaternion: list[float]
    ) -> float:
        object_to_reference_matrix = numpy.identity(4, dtype="float32")
        object_to_reference_matrix[0:3, 0:3] = Rotation.from_quat(object_to_reference_rotation_quaternion).as_matrix()
        object_to_reference_matrix[0:3, 3] = object_to_reference_translation
        object_points_reference = numpy.empty((len(object_points_target), 3), dtype="float32")
        for object_point_index, object_point_target in enumerate(object_points_target):
            object_point_reference = numpy.matmul(
                object_to_reference_matrix,
                [object_point_target[0], object_point_target[1], object_point_target[2], 1.0])
            object_points_reference[object_point_index, 0:3] = object_point_reference[0:3]
        detector_label: str = ray_set.detector_label
        reference_to_detector_matrix: Matrix4x4 = ray_set.detector_to_reference_matrix
        reference_to_detector: numpy.ndarray = reference_to_detector_matrix.as_numpy_array()
        reference_to_detector_rotation_vector = \
            Rotation.as_rotvec(Rotation.from_matrix(reference_to_detector[0:3, 0:3]))
        reference_to_detector_translation = reference_to_detector[0:3, 3]
        camera_matrix = numpy.array(self._intrinsics_by_detector_label[detector_label].get_matrix(), dtype="float32")
        camera_distortion_coefficients = \
            numpy.array(self._intrinsics_by_detector_label[detector_label].get_distortion_coefficients(),
                        dtype="float32")
        project_points_result = cv2.projectPoints(
            objectPoints=object_points_reference,
            rvec=reference_to_detector_rotation_vector,
            tvec=reference_to_detector_translation,
            cameraMatrix=camera_matrix,
            distCoeffs=camera_distortion_coefficients)
        projected_points = project_points_result[0]
        sum_reprojection_errors_squared: float = 0.0
        for point_index, image_point in enumerate(ray_set.image_points):
            reprojection_error_for_point = \
                numpy.linalg.norm(projected_points[point_index, 0, 0:2] - image_point)
            sum_reprojection_errors_squared += reprojection_error_for_point ** 2
        mean_reprojection_errors_squared: float = sum_reprojection_errors_squared / len(object_points_target)
        rms_reprojection_error = numpy.sqrt(mean_reprojection_errors_squared)
        return rms_reprojection_error

    @staticmethod
    def _denoise_is_pose_pair_outlier(
        pose_a_object_to_reference_matrix: numpy.ndarray,
        pose_b_object_to_reference_matrix: numpy.ndarray,
        parameters: PoseSolverParameters
    ) -> bool:

        position_a = pose_a_object_to_reference_matrix[0:3, 3]
        position_b = pose_b_object_to_reference_matrix[0:3, 3]
        distance_millimeters = numpy.linalg.norm(position_a - position_b)
        if distance_millimeters > parameters.DENOISE_OUTLIER_DISTANCE_MILLIMETERS:
            return True

        orientation_a = pose_a_object_to_reference_matrix[0:3, 0:3]
        orientation_b = pose_b_object_to_reference_matrix[0:3, 0:3]
        rotation_a_to_b = numpy.matmul(orientation_a, numpy.linalg.inv(orientation_b))
        angle_degrees = numpy.linalg.norm(Rotation.from_matrix(rotation_a_to_b).as_rotvec())
        if angle_degrees > parameters.DENOISE_OUTLIER_DISTANCE_MILLIMETERS:
            return True

        return False

    # Take an average of recent poses, with detection and removal of outliers
    # TODO: Currently not used - but it's probably a good feature to have
    def _denoise_detector_to_reference_pose(
        self,
        object_label: str,
        raw_poses: list[...]  # In order, oldest to newest
    ) -> ...:
        most_recent_pose = raw_poses[-1]
        max_storage_size: int = self._parameters.DENOISE_STORAGE_SIZE
        filter_size: int = self._parameters.DENOISE_FILTER_SIZE
        if filter_size <= 1 or max_storage_size <= 1:
            return most_recent_pose  # trivial case

        # find a consistent range of recent indices
        poses: list[...] = list(raw_poses)
        poses.reverse()  # now they are sorted so that the first element is most recent
        required_starting_streak: int = self._parameters.DENOISE_REQUIRED_STARTING_STREAK
        starting_index: int = -1  # not yet known, we want to find this
        if required_starting_streak <= 1:
            starting_index = 0  # trivial case
        else:
            current_inlier_streak: int = 1  # comparison always involves a streak of size 1 or more
            for pose_index in range(1, len(raw_poses)):
                if self._denoise_is_pose_pair_outlier(poses[pose_index - 1], poses[pose_index]):
                    current_inlier_streak = 1
                    continue
                current_inlier_streak += 1
                if current_inlier_streak >= required_starting_streak:
                    starting_index = pose_index - required_starting_streak + 1
                    break

        if starting_index < 0:
            if len(poses) >= max_storage_size:  # There appear to be enough poses, so data seems to be inconsistent
                print(
                    "Warning: Can't find consistent pose streak. "
                    "Will use most recent raw pose for object " + object_label + ".")
            return most_recent_pose

        poses_to_average: list[...] = [poses[starting_index]]
        for pose_index in range(starting_index + 1, len(poses)):
            if (not self._denoise_is_pose_pair_outlier(poses[pose_index - 1], poses[pose_index])) or \
               (not self._denoise_is_pose_pair_outlier(poses[starting_index], poses[pose_index])):
                poses_to_average.append(poses[pose_index])
                if len(poses_to_average) > filter_size:
                    break

        translations = [list(pose.object_to_reference_matrix[0:3, 3])
                        for pose in poses_to_average]
        orientations = [list(Rotation.from_matrix(pose.object_to_reference_matrix[0:3, 0:3]).as_quat(canonical=True))
                        for pose in poses_to_average]
        filtered_translation = average_vector(translations)
        filtered_orientation = average_quaternion(orientations)
        filtered_object_to_reference_matrix = numpy.identity(4, dtype="float32")
        filtered_object_to_reference_matrix[0:3, 0:3] = Rotation.from_quat(filtered_orientation).as_matrix()
        filtered_object_to_reference_matrix[0:3, 3] = filtered_translation
        # return PoseData(
        #     object_label=object_label,
        #     object_to_reference_matrix=filtered_object_to_reference_matrix,
        #     ray_sets=most_recent_pose.ray_sets)

    def update(self) -> None:
        if self._last_updated_timestamp_utc >= self._last_change_timestamp_utc:
            return

        if len(self._targets) == 0:
            return

        self._last_updated_timestamp_utc = datetime.datetime.utcnow()
        self._poses_by_detector_label.clear()
        self._poses_by_target_id.clear()

        corners: dict[str, dict[str, list[list[float]]]]  # [detector_label][marker_id][point_index][x/y]
        corners = {
            detector_label: detector_record.get_corners()
            for detector_label, detector_record in self._detector_records_by_detector_label.items()}
        detector_labels: list[str] = list(self._detector_records_by_detector_label.keys())

        for detector_label in detector_labels:
            if detector_label not in self._intrinsics_by_detector_label:
                # TODO: Output a suitable warning that no intrinsics have been received, but don't do it every frame
                del corners[detector_label]

        reference_target: TargetBase = self._targets[0]
        for detector_label in detector_labels:
            if detector_label in self._extrinsics_by_detector_label:
                self._poses_by_detector_label[detector_label] = self._extrinsics_by_detector_label[detector_label]
            else:
                intrinsics: IntrinsicParameters = self._intrinsics_by_detector_label[detector_label]
                reference_to_detector: Matrix4x4 = MathUtils.estimate_matrix_transform_to_detector(
                    target=reference_target,
                    corners_by_marker_id=corners[detector_label],
                    detector_intrinsics=intrinsics)
                detector_to_reference: Matrix4x4 = Matrix4x4.from_numpy_array(
                    numpy.linalg.inv(reference_to_detector.as_numpy_array()))
                self._poses_by_detector_label[detector_label] = detector_to_reference

        # At the time of writing, each marker_id can be used only once.
        # So we can remove marker_ids used by the reference_target to avoid unnecessary processing.
        for detector_label in detector_labels:
            for marker_id in reference_target.get_marker_ids():
                corners[detector_label].pop(marker_id)

        rays: dict[str, list[list[Ray]]] = dict()  # indexed as [marker_id][detector_index][corner_index]
        detector_labels_by_marker_id: dict[str, list[str]] = dict()
        for detector_label in detector_labels:
            detector_to_reference: Matrix4x4 = self._poses_by_detector_label[detector_label]
            intrinsics: IntrinsicParameters = self._intrinsics_by_detector_label[detector_label]
            ray_origin: list[float] = detector_to_reference.get_translation()
            ray_directions_by_marker_id: dict[str, list[list[float]]]  # [marker_id][point_index][x/y/z]
            ray_directions_by_marker_id = MathUtils.convert_detector_corners_to_vectors(
                corners_by_marker_id=corners[detector_label],
                detector_intrinsics=intrinsics,
                detector_to_reference_matrix=detector_to_reference)
            for marker_id, ray_directions in ray_directions_by_marker_id.items():
                if marker_id not in rays:
                    rays[marker_id] = list()
                rays[marker_id].append([
                    Ray(source_point=ray_origin, direction=ray_directions_by_marker_id[marker_id][corner_index])
                    for corner_index in range(0, _CORNER_COUNT)])
                if marker_id not in detector_labels_by_marker_id:
                    detector_labels_by_marker_id[marker_id] = list()
                detector_labels_by_marker_id[marker_id].append(detector_label)

        # intersect rays to find the 3D points for each marker corner in reference coordinates
        intersections_by_marker_id: dict[str, list[list[float]]] = dict()  # [marker_id][corner_index][x/y/z]
        standalone_rays_marker_ids: list[str] = list()
        for marker_id, rays_by_detector_index in rays.items():
            ray_list_by_corner_index: list[list[Ray]] = [[
                rays[marker_id][detector_index][corner_index]
                for detector_index in range(0, len(rays[marker_id]))]
                for corner_index in range(0, _CORNER_COUNT)]
            intersections_appear_valid: bool = True  # If something looks off, set this to False
            corners_reference_by_corner_index: list[list[float]] = list()
            for corner_index in range(0, _CORNER_COUNT):
                intersection_result = closest_intersection_between_n_lines(
                    rays=ray_list_by_corner_index[corner_index],
                    maximum_distance=self._parameters.INTERSECTION_MAXIMUM_DISTANCE)
                if intersection_result.centroids.shape[0] == 0:
                    intersections_appear_valid = False
                    break
                corners_reference_by_corner_index.append(list(intersection_result.centroid().flatten()))
            if not intersections_appear_valid:
                standalone_rays_marker_ids.append(marker_id)
                continue
            intersections_by_marker_id[marker_id] = corners_reference_by_corner_index

        # We estimate the pose of each target based on the calculated intersections
        # and the rays projected from each detector
        for target in self._targets:
            if target.target_id == str(reference_target.target_id):
                continue  # everything is expressed relative to the reference...
            detected_marker_ids_in_target: list[str] = target.get_marker_ids()

            marker_ids_with_intersections: list[str] = list()
            marker_ids_with_rays: list[str] = list()
            detector_labels: set[str] = set()
            for marker_id in detected_marker_ids_in_target:
                if marker_id in intersections_by_marker_id:
                    marker_ids_with_intersections.append(marker_id)
                if marker_id in standalone_rays_marker_ids:
                    marker_ids_with_rays.append(marker_id)
                if marker_id in detector_labels_by_marker_id:
                    for detector_label in detector_labels_by_marker_id[marker_id]:
                        detector_labels.add(detector_label)

            if len(marker_ids_with_intersections) <= 0 and len(marker_ids_with_rays) <= 0:
                continue  # No information on which to base a pose

            if len(detector_labels) < self._parameters.minimum_detector_count:
                continue

            # NB. len() == 0 or less for either of these indicates an internal error
            one_detector_only: bool = (len(detector_labels) == 1)
            if one_detector_only:
                # Note: there cannot be any intersections in this case
                detector_label: str = next(iter(detector_labels))
                intrinsics: IntrinsicParameters = self._intrinsics_by_detector_label[detector_label]
                detected_to_detector_matrix4x4: Matrix4x4 = MathUtils.estimate_matrix_transform_to_detector(
                    target=target,
                    corners_by_marker_id=corners[detector_label],
                    detector_intrinsics=intrinsics)
                detected_to_detector: numpy.ndarray = detected_to_detector_matrix4x4.as_numpy_array()
                detector_to_reference: numpy.ndarray = self._poses_by_detector_label[detector_label].as_numpy_array()
                detected_to_reference: numpy.ndarray = detector_to_reference @ detected_to_detector
                self._poses_by_target_id[target.target_id] = Matrix4x4.from_numpy_array(detected_to_reference)
            else:
                # Fill in the required variables for the customized iterative closest point
                detected_known_points: list[list[float]] = list(itertools.chain.from_iterable([
                    target.get_points_for_marker_id(marker_id)
                    for marker_id in marker_ids_with_intersections]))
                reference_known_points: list[list[float]] = list(itertools.chain.from_iterable([
                    intersections_by_marker_id[marker_id]
                    for marker_id in marker_ids_with_intersections]))
                detected_ray_points: list[list[float]] = list(itertools.chain.from_iterable([
                    target.get_points_for_marker_id(marker_id)
                    for marker_id in marker_ids_with_rays]))
                reference_rays: list[Ray] = list(itertools.chain.from_iterable([
                    rays[marker_id] for marker_id in marker_ids_with_rays]))
                iterative_closest_point_parameters = IterativeClosestPointParameters(
                    termination_iteration_count=self._parameters.icp_termination_iteration_count,
                    termination_delta_translation=self._parameters.icp_termination_translation,
                    termination_delta_rotation_radians=self._parameters.icp_termination_rotation_radians,
                    termination_mean_point_distance=self._parameters.icp_termination_mean_point_distance,
                    termination_rms_point_distance=self._parameters.icp_termination_rms_point_distance)
                if len(marker_ids_with_intersections) >= 1:
                    initial_detected_to_reference_matrix = register_corresponding_points(
                        point_set_from=detected_known_points,
                        point_set_to=reference_known_points,
                        collinearity_do_check=False)
                    icp_output = iterative_closest_point_for_points_and_rays(
                        source_known_points=detected_known_points,
                        target_known_points=reference_known_points,
                        source_ray_points=detected_ray_points,
                        target_rays=reference_rays,
                        initial_transformation_matrix=initial_detected_to_reference_matrix,
                        parameters=iterative_closest_point_parameters)
                else:
                    icp_output = iterative_closest_point_for_points_and_rays(
                        source_known_points=detected_known_points,
                        target_known_points=reference_known_points,
                        source_ray_points=detected_ray_points,
                        target_rays=reference_rays,
                        parameters=iterative_closest_point_parameters)
                detected_to_reference = icp_output.source_to_target_matrix
                self._poses_by_target_id[target.target_id] = Matrix4x4.from_numpy_array(detected_to_reference)
