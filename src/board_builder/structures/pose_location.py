import datetime

import numpy as np
from numpy._typing import NDArray
from typing import Any
from scipy.spatial.transform import Rotation as R
from src.pose_solver.util.average_quaternion import average_quaternion
from src.common.structures import Matrix4x4, Pose


class PoseLocation:

    _id: str
    _timestamp: str
    _TMatrix: NDArray[Any]
    _RMAT_list: list
    _TVEC_list: list

    def __init__(self, object_id):
        self._id = object_id
        self._timestamp = str(datetime.datetime.now())

        self._TMatrix = np.eye(4)
        self._RMAT_list = []  # Rotation matrix
        self._TVEC_list = []  # Translation vector

        self.frame_count = 0

    def add_matrix(self, transformation_matrix: Matrix4x4, timestamp: str):
        self._timestamp = timestamp

        self._RMAT_list.append(transformation_matrix[:3, :3])
        self._TVEC_list.append(transformation_matrix[:3, 3])

        avg_translation = np.mean(self._TVEC_list, axis=0)

        quaternions = [R.from_matrix(rot).as_quat(canonical=True) for rot in self._RMAT_list]
        quaternions = [[float(quaternion[i]) for i in range(0, 4)] for quaternion in quaternions]
        avg_quat = average_quaternion(quaternions)
        avg_rotation = R.from_quat(avg_quat).as_matrix()

        self._TMatrix[:3, :3] = avg_rotation
        self._TMatrix[:3, 3] = avg_translation

    def get_matrix(self):
        return self._TMatrix

    def get_average_pose(self):
        pose = Pose(
            target_id=self._id,
            object_to_reference_matrix=Matrix4x4.from_numpy_array(self._TMatrix),
            solver_timestamp_utc_iso8601=self._timestamp
        )
        return pose

    def get_median_pose(self):
        if not self._RMAT_list or not self._TVEC_list:
            raise ValueError("No matrices available to compute the median.")

        rmat_array = np.array(self._RMAT_list)
        tvec_array = np.array(self._TVEC_list)

        median_rmat = np.median(rmat_array, axis=0)
        median_tvec = np.median(tvec_array, axis=0)

        median_transformation_matrix = np.eye(4)
        median_transformation_matrix[:3, :3] = median_rmat
        median_transformation_matrix[:3, 3] = median_tvec

        pose = Pose(
            target_id=self._id,
            object_to_reference_matrix=Matrix4x4.from_numpy_array(median_transformation_matrix),
            solver_timestamp_utc_iso8601=self._timestamp
        )

        return pose
