from .api import \
    AddMarkerCornersRequest, \
    AddTargetMarkerRequest, \
    AddTargetMarkerResponse, \
    GetPosesRequest, \
    GetPosesResponse, \
    SetIntrinsicParametersRequest, \
    SetReferenceMarkerRequest, \
    StartPoseSolverRequest, \
    StopPoseSolverRequest
from .exceptions import PoseSolverException
from .fileio import PoseSolverConfiguration
from .pose_solver import PoseSolver
from .structures import \
    MarkerCorners, \
    TargetMarker
from src.common import \
    EmptyResponse, \
    ErrorResponse, \
    get_kwarg, \
    MCTComponent, \
    MCTRequest, \
    MCTResponse
from src.common.structures import \
    Pose, \
    PoseSolverStatus
import datetime
import logging
from typing import Callable

logger = logging.getLogger(__name__)


def dummy_function(_: dict) -> MCTResponse:
    return EmptyResponse()


class PoseSolverAPI(MCTComponent):
    """
    API-friendly layer overtop of a PoseSolver
    """
    _status: PoseSolverStatus
    _pose_solver: PoseSolver

    def __init__(
        self,
        configuration: PoseSolverConfiguration,
        pose_solver: PoseSolver
    ):
        super().__init__(
            status_source_label=configuration.serial_identifier,
            send_status_messages_to_logger=True)
        self._pose_solver = pose_solver
        self._status = PoseSolverStatus()

    async def internal_update(self):
        if self._status.solve_status == PoseSolverStatus.Solve.RUNNING:
            self._pose_solver.update()

    def supported_request_types(self) -> dict[type[MCTRequest], Callable[[dict], MCTResponse]]:
        return_value: dict[type[MCTRequest], Callable[[dict], MCTResponse]] = super().supported_request_types()
        return_value.update({
            AddMarkerCornersRequest: self.add_marker_corners,
            AddTargetMarkerRequest: self.add_target_marker,
            GetPosesRequest: self.get_poses,
            SetIntrinsicParametersRequest: self.set_intrinsic_parameters,
            SetReferenceMarkerRequest: self.set_reference_marker,
            StartPoseSolverRequest: self.start_pose_solver,
            StopPoseSolverRequest: self.stop_pose_solver})
        return return_value

    def add_marker_corners(self, **kwargs) -> EmptyResponse:
        request: AddMarkerCornersRequest = get_kwarg(
            kwargs=kwargs,
            key="request",
            arg_type=AddMarkerCornersRequest)
        detector_timestamp_utc: datetime.datetime = datetime.datetime.fromisoformat(
            request.detector_timestamp_utc_iso8601)  # TODO: ErrorResponse if formatted incorrectly?
        detected_corners: list[MarkerCorners] = [
            MarkerCorners(
                detector_label=request.detector_label,
                marker_id=int(detected_marker_snapshot.label),
                points=[
                    [detected_marker_snapshot.corner_image_points[i].x_px,
                     detected_marker_snapshot.corner_image_points[i].y_px]
                    for i in range(0, 4)],
                timestamp=detector_timestamp_utc)
            for detected_marker_snapshot in request.detected_marker_snapshots]
        self._pose_solver.add_marker_corners(detected_corners=detected_corners)
        return EmptyResponse()

    def add_target_marker(self, **kwargs) -> AddTargetMarkerResponse | ErrorResponse:
        request: AddTargetMarkerRequest = get_kwarg(
            kwargs=kwargs,
            key="request",
            arg_type=AddTargetMarkerRequest)
        try:
            target_id: str = self._pose_solver.add_target_marker(
                marker_id=request.marker_id,
                marker_diameter=request.marker_diameter)
        except PoseSolverException as e:
            return ErrorResponse(
                message=e.message)
        return AddTargetMarkerResponse(
            target_id=target_id)

    def get_poses(self, **_kwargs) -> GetPosesResponse:
        detector_poses: list[Pose]
        target_poses: list[Pose]
        detector_poses, target_poses = self._pose_solver.get_poses()
        return GetPosesResponse(
            detector_poses=detector_poses,
            target_poses=target_poses)

    def set_intrinsic_parameters(self, **kwargs) -> EmptyResponse | ErrorResponse:
        request: SetIntrinsicParametersRequest = get_kwarg(
            kwargs=kwargs,
            key="request",
            arg_type=SetIntrinsicParametersRequest)
        self._pose_solver.set_intrinsic_parameters(
            detector_label=request.detector_label,
            intrinsic_parameters=request.intrinsic_parameters)
        return EmptyResponse()

    def set_reference_marker(self, **kwargs) -> EmptyResponse | ErrorResponse:
        request: SetReferenceMarkerRequest = get_kwarg(
            kwargs=kwargs,
            key="request",
            arg_type=SetReferenceMarkerRequest)
        try:
            self._pose_solver.set_reference_target(
                TargetMarker(
                    marker_id=request.marker_id,
                    marker_size=request.marker_diameter))
        except PoseSolverException as e:
            return ErrorResponse(
                message=e.message)
        return EmptyResponse()

    def start_pose_solver(self, **_kwargs) -> EmptyResponse:
        self._status.solve_status = PoseSolverStatus.Solve.RUNNING
        return EmptyResponse()

    def stop_pose_solver(self, **_kwargs) -> EmptyResponse:
        self._status.solve_status = PoseSolverStatus.Solve.STOPPED
        return EmptyResponse()
