from .api import \
    PoseSolverAddDetectorFrameRequest, \
    PoseSolverAddTargetMarkerRequest, \
    PoseSolverGetPosesRequest, \
    PoseSolverGetPosesResponse, \
    PoseSolverSetIntrinsicRequest, \
    PoseSolverSetReferenceRequest, \
    PoseSolverStartRequest, \
    PoseSolverStopRequest
from .exceptions import PoseSolverException
from .pose_solver import PoseSolver
from .structures import \
from src.common import \
    EmptyResponse, \
    ErrorResponse, \
    get_kwarg, \
    MCTComponent, \
    MCTRequest, \
    MCTResponse
from src.common.structures import \
    Pose, \
    PoseSolverStatus, \
    MarkerCorners
import logging
from typing import Callable


logger = logging.getLogger(__name__)


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

    def add_detector_frame(self, **kwargs) -> EmptyResponse | ErrorResponse:
        request: PoseSolverAddDetectorFrameRequest = get_kwarg(
            kwargs=kwargs,
            key="request",
            arg_type=PoseSolverAddDetectorFrameRequest)
        try:
            self._pose_solver.add_detector_frame(
                detector_label=request.detector_label,
                detector_frame=request.detector_frame)
        except PoseSolverException as e:
            return ErrorResponse(message=e.message)
        return EmptyResponse()

    def add_target(self, **kwargs) -> EmptyResponse | ErrorResponse:
        request: PoseSolverAddTargetMarkerRequest = get_kwarg(
            kwargs=kwargs,
            key="request",
            arg_type=PoseSolverAddTargetMarkerRequest)
        try:
            self._pose_solver.add_target(target=request.target)
        except PoseSolverException as e:
            return ErrorResponse(message=e.message)
        return EmptyResponse()

    def get_poses(self, **_kwargs) -> PoseSolverGetPosesResponse | ErrorResponse:
        detector_poses: list[Pose]
        target_poses: list[Pose]
        try:
            detector_poses, target_poses = self._pose_solver.get_poses()
        except PoseSolverException as e:
            return ErrorResponse(message=e.message)
        return PoseSolverGetPosesResponse(
            detector_poses=detector_poses,
            target_poses=target_poses)

    def set_intrinsic_parameters(self, **kwargs) -> EmptyResponse | ErrorResponse:
        request: PoseSolverSetIntrinsicRequest = get_kwarg(
            kwargs=kwargs,
            key="request",
            arg_type=PoseSolverSetIntrinsicRequest)
        try:
            self._pose_solver.set_intrinsic_parameters(
                detector_label=request.detector_label,
                intrinsic_parameters=request.intrinsic_parameters)
        except PoseSolverException as e:
            return ErrorResponse(message=e.message)
        return EmptyResponse()

    def set_reference_marker(self, **kwargs) -> EmptyResponse | ErrorResponse:
        request: PoseSolverSetReferenceRequest = get_kwarg(
            kwargs=kwargs,
            key="request",
            arg_type=PoseSolverSetReferenceRequest)
        try:
            self._pose_solver.set_reference_target(target_id=str(request.marker_id))
        except PoseSolverException as e:
            return ErrorResponse(message=e.message)
        return EmptyResponse()

    def start_pose_solver(self, **_kwargs) -> EmptyResponse:
        self._status.solve_status = PoseSolverStatus.Solve.RUNNING
        return EmptyResponse()

    def stop_pose_solver(self, **_kwargs) -> EmptyResponse:
        self._status.solve_status = PoseSolverStatus.Solve.STOPPED
        return EmptyResponse()

    def supported_request_types(self) -> dict[type[MCTRequest], Callable[[dict], MCTResponse]]:
        return_value: dict[type[MCTRequest], Callable[[dict], MCTResponse]] = super().supported_request_types()
        return_value.update({
            PoseSolverAddDetectorFrameRequest: self.add_detector_frame,
            PoseSolverAddTargetMarkerRequest: self.add_target,
            PoseSolverGetPosesRequest: self.get_poses,
            PoseSolverSetIntrinsicRequest: self.set_intrinsic_parameters,
            PoseSolverSetReferenceRequest: self.set_reference_marker,
            PoseSolverStartRequest: self.start_pose_solver,
            PoseSolverStopRequest: self.stop_pose_solver})
        return return_value

    async def update(self):
        if self._status.solve_status == PoseSolverStatus.Solve.RUNNING:
            self._pose_solver.update()
