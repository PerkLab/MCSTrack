from src.common.structures.pose_solver_frame import PoseSolverFrame
from .mct_component_address import MCTComponentAddress
from .connection import Connection
from src.common.api import \
    EmptyResponse, \
    MCTRequest, \
    MCTRequestSeries, \
    MCTResponse, \
    MCTResponseSeries
from src.common.structures import \
    KeyValueSimpleAny, \
    Pose, \
    TargetBase
from src.pose_solver.api import \
    PoseSolverGetPosesResponse, \
    PoseSolverSetTargetsRequest, \
    PoseSolverStartRequest, \
    PoseSolverStopRequest
import datetime
import uuid


class PoseSolverConnection(Connection):

    # These are variables used directly by the MCTController for storing data

    configured_solver_parameters: list[KeyValueSimpleAny] | None
    configured_targets: list[TargetBase] | None

    request_id: uuid.UUID | None
    detector_poses: list[Pose]
    target_poses: list[Pose]
    detector_timestamps: dict[str, datetime.datetime]  # access by detector_label
    poses_timestamp: datetime.datetime
    recording: list[PoseSolverFrame] | None

    def __init__(
        self,
        component_address: MCTComponentAddress
    ):
        super().__init__(component_address=component_address)

        self.configured_solver_parameters = None
        self.configured_targets = None

        self.request_id = None
        self.detector_poses = list()
        self.target_poses = list()
        self.detector_timestamps = dict()
        self.poses_timestamp = datetime.datetime.min
        self.recording = []

    def create_deinitialization_request_series(self) -> MCTRequestSeries:
        return MCTRequestSeries(series=[PoseSolverStopRequest()])

    def create_initialization_request_series(self) -> MCTRequestSeries:
        series: list[MCTRequest] = [PoseSolverStartRequest()]
        if self.configured_targets is not None:
            series.append(PoseSolverSetTargetsRequest(targets=self.configured_targets))
        return MCTRequestSeries(series=series)

    def handle_deinitialization_response_series(
        self,
        response_series: MCTResponseSeries
    ) -> Connection.DeinitializationResult:
        response_count: int = len(response_series.series)
        if response_count != 1:
            self.enqueue_status_message(
                severity="warning",
                message=f"Expected exactly one response to deinitialization requests. Got {response_count}.")
        elif not isinstance(response_series.series[0], EmptyResponse):
            self.enqueue_status_message(
                severity="warning",
                message=f"The deinitialization response was not of the expected type EmptyResponse.")
        return Connection.DeinitializationResult.SUCCESS

    def handle_initialization_response_series(
        self,
        response_series: MCTResponseSeries
    ) -> Connection.InitializationResult:
        response_count: int = len(response_series.series)
        if response_count != 1:
            self.enqueue_status_message(
                severity="warning",
                message=f"Expected exactly one response to initialization requests. Got {response_count}.")
        elif not isinstance(response_series.series[0], EmptyResponse):
            self.enqueue_status_message(
                severity="warning",
                message=f"The initialization response was not of the expected type EmptyResponse.")
        return Connection.InitializationResult.SUCCESS

    def supported_response_types(self) -> list[type[MCTResponse]]:
        return super().supported_response_types() + [
            PoseSolverGetPosesResponse]
