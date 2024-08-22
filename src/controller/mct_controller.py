from .exceptions import ResponseSeriesNotExpected
from .structures import \
    ConnectionReport, \
    Connection, \
    DetectorConnection, \
    MCTComponentAddress, \
    MCTComponentConfig, \
    MCTConfiguration, \
    PoseSolverConnection, \
    StartupMode
from src.common import \
    EmptyResponse, \
    ErrorResponse, \
    MCTComponent, \
    MCTRequest, \
    MCTRequestSeries, \
    MCTResponse, \
    MCTResponseSeries, \
    StatusMessageSource, \
    TimestampGetRequest, \
    TimestampGetResponse, \
    TimeSyncStartRequest, \
    TimeSyncStopRequest
from src.common.structures import \
    ComponentRoleLabel, \
    COMPONENT_ROLE_LABEL_DETECTOR, \
    COMPONENT_ROLE_LABEL_POSE_SOLVER, \
    DetectorFrame, \
    IntrinsicParameters, \
    PoseSolverFrame
from src.detector.api import \
    CalibrationResultGetActiveRequest, \
    CalibrationResultGetActiveResponse, \
    CameraResolutionGetRequest, \
    CameraResolutionGetResponse, \
    DetectorFrameGetRequest, \
    DetectorFrameGetResponse
from src.pose_solver.api import \
    PoseSolverAddDetectorFrameRequest, \
    PoseSolverGetPosesRequest, \
    PoseSolverGetPosesResponse, \
    PoseSolverSetExtrinsicRequest, \
    PoseSolverSetIntrinsicRequest
import datetime
from enum import IntEnum, StrEnum
import hjson
from ipaddress import IPv4Address
import json
import logging
import numpy
import os
from pydantic import ValidationError
from typing import Callable, Final, get_args, TypeVar
import uuid

logger = logging.getLogger(__name__)
ConnectionType = TypeVar('ConnectionType', bound=Connection)


_TIME_SYNC_SAMPLE_MAXIMUM_COUNT: Final[int] = 5


class MCTController(MCTComponent):

    class Status(StrEnum):
        STOPPED: Final[int] = "Idle"
        STARTING: Final[int] = "Starting"
        RUNNING: Final[int] = "Running"
        STOPPING: Final[int] = "Stopping"

    class StartupState(IntEnum):
        INITIAL: Final[int] = 0
        CONNECTING: Final[int] = 1
        TIME_SYNC_START: Final[int] = 2
        TIME_SYNC_STOP: Final[int] = 3
        GET_INTRINSICS: Final[int] = 4
        SET_INTRINSICS: Final[int] = 5

    _status_message_source: StatusMessageSource
    _status: Status
    _startup_mode: StartupMode
    _startup_state: StartupState

    _connections: dict[str, Connection]
    _pending_request_ids: list[uuid.UUID]

    _recording_detector: bool
    _recording_pose_solver: bool
    _recording_save_path: str | None

    _time_sync_sample_count: int

    def __init__(
        self,
        serial_identifier: str,
        send_status_messages_to_logger: bool = False
    ):
        super().__init__(
            status_source_label=serial_identifier,
            send_status_messages_to_logger=send_status_messages_to_logger)
        self.status_message_source = StatusMessageSource(
            source_label="controller",
            send_to_logger=True)
        # _reset is responsible for creating and restoring the initial state; __init__ calls it to avoid duplication
        self._reset()

    def add_connections_from_configuration(
        self,
        configuration: MCTConfiguration
    ):
        def is_valid_ip_address(connection: MCTComponentConfig) -> bool:
            try:
                IPv4Address(connection.ip_address)
            except ValueError:
                self.add_status_message(
                    severity="error",
                    message=f"Connection {connection.label} has invalid IP address {connection.ip_address}. "
                            "It will be skipped.")
                return False
            if connection.port < 0 or connection.port > 65535:
                self.add_status_message(
                    severity="error",
                    message=f"Connection {connection.label} has invalid port {connection.port}. "
                            "It will be skipped.")
                return False
            return True

        for detector in configuration.detectors:
            if not is_valid_ip_address(detector):
                continue
            component_address: MCTComponentAddress = MCTComponentAddress(
                label=detector.label,
                role="detector",
                ip_address=detector.ip_address,
                port=detector.port)
            detector_connection: DetectorConnection = self.add_connection(component_address=component_address)
            if detector.fixed_transform_to_reference is not None:
                detector_connection.configured_transform_to_reference = detector.fixed_transform_to_reference
            if detector.camera_parameters is not None:
                detector_connection.configured_camera_parameters = detector.camera_parameters
            if detector.marker_parameters is not None:
                detector_connection.configured_marker_parameters = detector.marker_parameters
        for pose_solver in configuration.pose_solvers:
            if not is_valid_ip_address(pose_solver):
                continue
            component_address: MCTComponentAddress = MCTComponentAddress(
                label=pose_solver.label,
                role="pose_solver",
                ip_address=pose_solver.ip_address,
                port=pose_solver.port)
            pose_solver_connection: PoseSolverConnection = self.add_connection(component_address=component_address)
            if pose_solver.solver_parameters is not None:
                pose_solver_connection.configured_solver_parameters = pose_solver.solver_parameters
            if pose_solver.targets is not None:
                pose_solver_connection.configured_targets = pose_solver.targets

    def add_connection(
        self,
        component_address: MCTComponentAddress
    ) -> DetectorConnection | PoseSolverConnection:
        label = component_address.label
        if label in self._connections:
            raise RuntimeError(f"Connection associated with {label} already exists.")
        if component_address.role == COMPONENT_ROLE_LABEL_DETECTOR:
            return_value: DetectorConnection = DetectorConnection(component_address=component_address)
            self._connections[label] = return_value
            return return_value
        elif component_address.role == COMPONENT_ROLE_LABEL_POSE_SOLVER:
            return_value: PoseSolverConnection = PoseSolverConnection(component_address=component_address)
            self._connections[label] = return_value
            return return_value
        else:
            raise ValueError(f"Unrecognized component role {component_address.role}.")

    def _advance_startup_state(self) -> None:
        if len(self._pending_request_ids) <= 0 and self._startup_state == MCTController.StartupState.CONNECTING:
            self.status_message_source.enqueue_status_message(
                severity="debug",
                message="CONNECTING complete")
            component_labels: list[str] = self.get_component_labels(active=True)
            request_series: MCTRequestSeries = MCTRequestSeries(series=[TimeSyncStartRequest()])
            for component_label in component_labels:
                connection = self._get_connection(
                    connection_label=component_label,
                    connection_type=Connection)
                connection.reset_time_sync_stats()
                self._pending_request_ids.append(
                    self.request_series_push(
                        connection_label=component_label,
                        request_series=request_series))
            self._time_sync_sample_count = 0
            self._startup_state = MCTController.StartupState.TIME_SYNC_START
        if len(self._pending_request_ids) <= 0 and self._startup_state == MCTController.StartupState.TIME_SYNC_START:
            self.status_message_source.enqueue_status_message(
                severity="debug",
                message="TIME_SYNC complete")
            component_labels: list[str] = self.get_component_labels(active=True)
            request_series: MCTRequestSeries = MCTRequestSeries(series=[
                TimestampGetRequest(requester_timestamp_utc_iso8601=datetime.datetime.utcnow().isoformat())])
            for component_label in component_labels:
                self._pending_request_ids.append(
                    self.request_series_push(
                        connection_label=component_label,
                        request_series=request_series))
            self._time_sync_sample_count += 1
            if self._time_sync_sample_count >= _TIME_SYNC_SAMPLE_MAXIMUM_COUNT:
                request_series: MCTRequestSeries = MCTRequestSeries(series=[TimeSyncStopRequest()])
                for component_label in component_labels:
                    self._pending_request_ids.append(
                        self.request_series_push(
                            connection_label=component_label,
                            request_series=request_series))
                self._startup_state = MCTController.StartupState.TIME_SYNC_STOP
        if len(self._pending_request_ids) <= 0 and self._startup_state == MCTController.StartupState.TIME_SYNC_STOP:
            self.status_message_source.enqueue_status_message(
                severity="debug",
                message="STARTING_CAPTURE complete")
            detector_labels: list[str] = self.get_active_detector_labels()
            for detector_label in detector_labels:
                request_series: MCTRequestSeries = MCTRequestSeries(
                    series=[
                        CameraResolutionGetRequest(),
                        CalibrationResultGetActiveRequest()])
                self._pending_request_ids.append(self.request_series_push(
                    connection_label=detector_label,
                    request_series=request_series))
            self._startup_state = MCTController.StartupState.GET_INTRINSICS
        if len(self._pending_request_ids) <= 0 and self._startup_state == MCTController.StartupState.GET_INTRINSICS:
            self.status_message_source.enqueue_status_message(
                severity="debug",
                message="GET_INTRINSICS complete")
            if self._startup_mode == StartupMode.DETECTING_ONLY:
                self._startup_state = MCTController.StartupState.INITIAL
                self._status = MCTController.Status.RUNNING  # We're done
            else:
                pose_solver_labels: list[str] = self.get_active_pose_solver_labels()
                for pose_solver_label in pose_solver_labels:
                    requests: list[MCTRequest] = list()
                    for detector_label in self.get_active_detector_labels():
                        detector_connection: DetectorConnection = self._get_connection(
                            connection_label=detector_label,
                            connection_type=DetectorConnection)
                        if detector_connection is None:
                            self.status_message_source.enqueue_status_message(
                                severity="error",
                                message=f"Failed to find DetectorConnection with label {detector_label}.")
                            continue
                        if detector_connection.current_intrinsic_parameters is not None:
                            requests.append(PoseSolverSetIntrinsicRequest(
                                detector_label=detector_label,
                                intrinsic_parameters=detector_connection.current_intrinsic_parameters))
                        if detector_connection.configured_transform_to_reference is not None:
                            requests.append(PoseSolverSetExtrinsicRequest(
                                detector_label=detector_label,
                                transform_to_reference=detector_connection.configured_transform_to_reference))
                    request_series: MCTRequestSeries = MCTRequestSeries(series=requests)
                    self._pending_request_ids.append(self.request_series_push(
                        connection_label=pose_solver_label,
                        request_series=request_series))
                self._startup_state = MCTController.StartupState.SET_INTRINSICS
        if len(self._pending_request_ids) <= 0 and self._startup_state == MCTController.StartupState.SET_INTRINSICS:
            self.status_message_source.enqueue_status_message(
                severity="debug",
                message="SET_INTRINSICS complete")
            self._startup_state = MCTController.StartupState.INITIAL
            self._status = MCTController.Status.RUNNING

    def contains_connection_label(self, label: str) -> bool:
        return label in self._connections

    def get_active_detector_labels(self) -> list[str]:
        """
        See get_component_labels.
        """
        return self.get_component_labels(role=COMPONENT_ROLE_LABEL_DETECTOR, active=True)

    def get_active_pose_solver_labels(self) -> list[str]:
        """
        See get_component_labels.
        """
        return self.get_component_labels(role=COMPONENT_ROLE_LABEL_POSE_SOLVER, active=True)

    def get_component_labels(
        self,
        role: str | None = None,
        active: bool | None = None
    ) -> list[str]:
        """
        Return the list of all labels corresponding to components of the given `role`, and given `active` state.
        None provided to `role` or `active` is treated as a wildcard (i.e. not filtered on that criteria).
        """
        if role is not None:
            valid_roles: list[str] = list(get_args(ComponentRoleLabel))
            if role not in valid_roles:
                raise ValueError(f"role must be among the valid values {str(valid_roles)}")
        return_value: list[str] = list()
        for connection_label, connection in self._connections.items():
            if role is not None and connection.get_role() != role:
                continue
            if active is not None and connection.is_active() != active:
                continue
            return_value.append(connection_label)
        return return_value

    def get_connection_reports(self) -> list[ConnectionReport]:
        return_value: list[ConnectionReport] = list()
        for connection in self._connections.values():
            return_value.append(connection.get_report())
        return return_value

    def _get_connection(
        self,
        connection_label: str,
        connection_type: type[ConnectionType]
    ) -> ConnectionType | None:
        if connection_label not in self._connections:
            return None
        connection: ConnectionType = self._connections[connection_label]
        if not isinstance(connection, connection_type):
            return None
        return connection

    def get_live_detector_intrinsics(
        self,
        detector_label: str
    ) -> IntrinsicParameters | None:
        """
        returns None if the detector does not exist, or if it has not been started.
        """
        detector_connection: DetectorConnection = self._get_connection(
            connection_label=detector_label,
            connection_type=DetectorConnection)
        if detector_connection is None:
            return None
        return detector_connection.current_intrinsic_parameters

    def get_live_detector_frame(
        self,
        detector_label: str
    ) -> DetectorFrame | None:
        """
        returns None if the detector does not exist, or has not been started, or if it has not yet gotten frames.
        """
        detector_connection: DetectorConnection = self._get_connection(
            connection_label=detector_label,
            connection_type=DetectorConnection)
        if detector_connection is None:
            return None
        return detector_connection.latest_frame

    def get_live_pose_solver_frame(
        self,
        pose_solver_label: str
    ) -> PoseSolverFrame | None:
        """
        returns None if the pose solver does not exist, or has not been started, or if it has not yet gotten frames.
        """
        pose_solver_connection: PoseSolverConnection = self._get_connection(
            connection_label=pose_solver_label,
            connection_type=PoseSolverConnection)
        if pose_solver_connection is None:
            return None
        return PoseSolverFrame(
            detector_poses=pose_solver_connection.detector_poses,
            target_poses=pose_solver_connection.target_poses,
            timestamp_utc_iso8601=pose_solver_connection.poses_timestamp.isoformat())

    def get_status(self) -> Status:
        return self._status

    def handle_error_response(
        self,
        response: ErrorResponse
    ):
        self.status_message_source.enqueue_status_message(
            severity="error",
            message=f"Received error: {response.message}")

    def handle_response_calibration_result_get_active(
        self,
        response: CalibrationResultGetActiveResponse,
        detector_label: str
    ) -> None:
        detector_connection: DetectorConnection = self._get_connection(
            connection_label=detector_label,
            connection_type=DetectorConnection)
        if detector_connection is None:
            self.status_message_source.enqueue_status_message(
                severity="error",
                message=f"Failed to find DetectorConnection with label {detector_label}.")
            return
        if response.intrinsic_calibration is None:
            if detector_connection.current_resolution is None:
                self.status_message_source.enqueue_status_message(
                    severity="error",
                    message=f"No calibration was found for detector {detector_label}, and failed to get resolution.")
                return
            self.status_message_source.enqueue_status_message(
                severity="warning",
                message=f"No calibration was found for detector {detector_label}. "
                        f"Zero parameters for active resolution {detector_connection.current_resolution} will be used.")
            detector_connection.current_intrinsic_parameters = IntrinsicParameters.generate_zero_parameters(
                resolution_x_px=detector_connection.current_resolution.x_px,
                resolution_y_px=detector_connection.current_resolution.y_px)
            return
        detector_connection.current_intrinsic_parameters = response.intrinsic_calibration.calibrated_values

    def handle_response_camera_resolution_get(
        self,
        response: CameraResolutionGetResponse,
        detector_label: str
    ) -> None:
        detector_connection: DetectorConnection = self._get_connection(
            connection_label=detector_label,
            connection_type=DetectorConnection)
        if detector_connection is None:
            self.status_message_source.enqueue_status_message(
                severity="error",
                message=f"Failed to find DetectorConnection with label {detector_label}.")
            return
        detector_connection.current_resolution = response.resolution

    def handle_response_detector_frame_get(
        self,
        response: DetectorFrameGetResponse,
        detector_label: str
    ):
        detector_connection: DetectorConnection = self._get_connection(
            connection_label=detector_label,
            connection_type=DetectorConnection)
        if detector_connection is None:
            self.status_message_source.enqueue_status_message(
                severity="error",
                message=f"Failed to find DetectorConnection with label {detector_label}.")
            return
        frame: DetectorFrame = response.frame
        adjusted_timestamp_utc: datetime.datetime = \
            frame.timestamp_utc() - datetime.timedelta(seconds=detector_connection.controller_offset_seconds)
        frame.timestamp_utc_iso8601 = adjusted_timestamp_utc.isoformat()
        detector_connection.latest_frame = frame

    def handle_response_get_poses(
        self,
        response: PoseSolverGetPosesResponse,
        pose_solver_label: str
    ) -> None:
        pose_solver_connection: PoseSolverConnection = self._get_connection(
            connection_label=pose_solver_label,
            connection_type=PoseSolverConnection)
        if pose_solver_connection is None:
            self.status_message_source.enqueue_status_message(
                severity="error",
                message=f"Failed to find PoseSolverConnection with label {pose_solver_label}.")
            return
        pose_solver_connection.detector_poses = response.detector_poses
        pose_solver_connection.target_poses = response.target_poses
        pose_solver_connection.poses_timestamp = (
            datetime.datetime.utcnow() -  # TODO: This should come from the pose solver
            datetime.timedelta(seconds=pose_solver_connection.controller_offset_seconds))

    def handle_response_timestamp_get(
        self,
        response: TimestampGetResponse,
        component_label: str
    ) -> None:
        connection: Connection = self._get_connection(
            connection_label=component_label,
            connection_type=Connection)
        utc_now: datetime.datetime = datetime.datetime.utcnow()
        requester_timestamp: datetime.datetime
        requester_timestamp = datetime.datetime.fromisoformat(response.requester_timestamp_utc_iso8601)
        round_trip_seconds: float = (utc_now - requester_timestamp).total_seconds()
        connection.network_latency_samples_seconds.append(round_trip_seconds)
        responder_timestamp: datetime.datetime
        responder_timestamp = datetime.datetime.fromisoformat(response.responder_timestamp_utc_iso8601)
        network_plus_offset_seconds: float = (responder_timestamp - requester_timestamp).total_seconds()
        connection.network_plus_offset_samples_seconds.append(network_plus_offset_seconds)
        if self._time_sync_sample_count >= _TIME_SYNC_SAMPLE_MAXIMUM_COUNT:
            connection.network_latency_seconds = numpy.median(connection.network_latency_samples_seconds)
            connection.controller_offset_samples_seconds = [
                network_plus_offset_sample_seconds - (connection.network_latency_seconds / 2.0)
                for network_plus_offset_sample_seconds in connection.network_plus_offset_samples_seconds]
            connection.controller_offset_seconds = numpy.median(connection.controller_offset_samples_seconds)
            print(f"Calculated offset to {connection.get_label()}: {connection.controller_offset_seconds}")

    def handle_response_unknown(
        self,
        response: MCTResponse
    ):
        self.status_message_source.enqueue_status_message(
            severity="error",
            message=f"Received unexpected response: {str(type(response))}")

    def handle_response_series(
        self,
        response_series: MCTResponseSeries,
        task_description: str | None = None,
        expected_response_count: int | None = None
    ) -> bool:
        if expected_response_count is not None:
            response_count: int = len(response_series.series)
            task_text: str = str()
            if task_description is not None:
                task_text = f" during {task_description}"
            if response_count < expected_response_count:
                self.status_message_source.enqueue_status_message(
                    severity="warning",
                    message=f"Received a response series{task_text}, "
                            f"but it contained fewer responses ({response_count}) "
                            f"than expected ({expected_response_count}).")
            elif response_count > expected_response_count:
                self.status_message_source.enqueue_status_message(
                    severity="warning",
                    message=f"Received a response series{task_text}, "
                            f"but it contained more responses ({response_count}) "
                            f"than expected ({expected_response_count}).")

        success: bool = True
        response: MCTResponse
        for response in response_series.series:
            if isinstance(response, CalibrationResultGetActiveResponse):
                self.handle_response_calibration_result_get_active(
                    response=response,
                    detector_label=response_series.responder)
            elif isinstance(response, CameraResolutionGetResponse):
                self.handle_response_camera_resolution_get(
                    response=response,
                    detector_label=response_series.responder)
            elif isinstance(response, DetectorFrameGetResponse):
                self.handle_response_detector_frame_get(
                    response=response,
                    detector_label=response_series.responder)
            elif isinstance(response, TimestampGetResponse):
                self.handle_response_timestamp_get(
                    response=response,
                    component_label=response_series.responder)
            elif isinstance(response, PoseSolverGetPosesResponse):
                self.handle_response_get_poses(
                    response=response,
                    pose_solver_label=response_series.responder)
            elif isinstance(response, ErrorResponse):
                self.handle_error_response(response=response)
                success = False
            elif not isinstance(response, EmptyResponse):
                self.handle_response_unknown(response=response)
                success = False
        return success

    def is_idle(self):
        return self._status == MCTController.Status.STOPPED

    def is_running(self):
        return self._status == MCTController.Status.RUNNING

    def is_transitioning(self):
        return self._status == MCTController.Status.STARTING or self._status == MCTController.Status.STOPPING

    def recording_start(
            self,
            save_path : str,
            record_pose_solver : bool,
            record_detector : bool
        ):

        if save_path:
            self._recording_pose_solver = record_pose_solver
            self._recording_detector = record_detector
            self._recording_save_path = save_path
        else:
            self.add_status_message(
                severity="error",
                message=f"Recording save path not defined")

    def recording_stop(self):
        for connection_label in self._connections:
            connection = self._get_connection(
                connection_label=connection_label,
                connection_type=Connection)
            report = connection.get_report()
            # Do not record if specified
            if report.role == COMPONENT_ROLE_LABEL_DETECTOR and not self._recording_detector:
                continue
            if report.role == COMPONENT_ROLE_LABEL_POSE_SOLVER and not self._recording_pose_solver:
                continue

            if self._recording_save_path is not None:
                frames_dict = [frame.dict() for frame in connection.recording]
                frames_json = json.dumps(frames_dict)
                with open(os.path.join(self._recording_save_path, report.role+"_log.json"), 'w') as f:
                    f.write(frames_json)

        self._recording_detector = False
        self._recording_pose_solver = False

    def remove_connection(
        self,
        label: str
    ):
        if label not in self._connections:
            raise RuntimeError(f"Failed to find connection associated with {label}.")
        self._connections.pop(label)

    def _reset(self):
        self._status = MCTController.Status.STOPPED
        self._startup_mode = StartupMode.DETECTING_AND_SOLVING  # Will be overwritten on startup
        self._startup_state = MCTController.StartupState.INITIAL

        self._connections = dict()
        self._pending_request_ids = list()

        self._recording_detector = False
        self._recording_pose_solver = False
        self._recording_save_path = None

        self._time_sync_sample_count = 0

    def request_series_push(
        self,
        connection_label: str,
        request_series: MCTRequestSeries
    ) -> uuid.UUID:
        if connection_label not in self._connections:
            raise RuntimeError(f"Failed to find connection with label {connection_label}.")
        elif not self._connections[connection_label].is_active():
            raise RuntimeError(f"Connection with label {connection_label} is not active.")
        return self._connections[connection_label].enqueue_request_series(
            request_series=request_series)

    def response_series_pop(
        self,
        request_series_id: uuid.UUID
    ) -> tuple[uuid.UUID | None, MCTResponseSeries | None]:
        """
        Only "pop" if there is a response (not None).
        Return value is a tuple whose elements comprise:
          - UUID of the request if no response has been received, or None
          - MCTResponseSeries if a response has been received, or None
        The dual return values allow easier reassignment of completed request ID's in calling code
        """
        for connection in self._connections.values():
            response_result: Connection.PopResponseSeriesResult = connection.pop_response_series_if_responded(
                request_series_id=request_series_id)
            if response_result.status == Connection.PopResponseSeriesResult.Status.UNTRACKED:
                continue
            elif response_result.status == Connection.PopResponseSeriesResult.Status.RESPONDED:
                return None, response_result.response_series
            else:  # queued, in progress
                return request_series_id, None  # Connection is tracking desired request series, but awaiting response
        # Cannot be found
        raise ResponseSeriesNotExpected()

    def start_from_configuration_filepath(
        self,
        input_configuration_filepath: str
    ) -> None:
        if self._status != MCTController.Status.STOPPED:
            raise RuntimeError("Cannot load from configuration if controller isn't first stopped.")
        if not os.path.exists(input_configuration_filepath):
            raise IOError(f"File {input_configuration_filepath} does not exist. Configuration will not be loaded.")
        if not os.path.isfile(input_configuration_filepath):
            raise IOError(f"File {input_configuration_filepath} is not a file. Configuration will not be loaded.")
        configuration_dict: dict
        with open(input_configuration_filepath, 'r') as infile:
            configuration_dict = hjson.loads(infile.read())
        configuration: MCTConfiguration
        try:
            configuration = MCTConfiguration(**configuration_dict)
        except ValidationError as e:
            raise RuntimeError(
                f"Failed to load configuration file {input_configuration_filepath}. "
                f"Error: {e}") from None
        self._reset()
        self.add_connections_from_configuration(configuration)
        self.start_up(mode=configuration.startup_mode)

    def start_up(
        self,
        mode: str = StartupMode.DETECTING_AND_SOLVING
    ) -> None:
        if mode not in StartupMode:
            raise ValueError(f"Unexpected mode \"{mode}\".")
        self._startup_mode = StartupMode(mode)

        if self._status != MCTController.Status.STOPPED:
            raise RuntimeError("Cannot start up if controller isn't first stopped.")
        for connection in self._connections.values():
            if mode == StartupMode.DETECTING_ONLY and \
               connection.get_role() == COMPONENT_ROLE_LABEL_POSE_SOLVER:
                continue
            connection.start_up()

        self._startup_state = MCTController.StartupState.CONNECTING
        self._status = MCTController.Status.STARTING

        self.recording_start(save_path="/home/adminpi5",
                             record_pose_solver=True,
                             record_detector=True)

    def shut_down(self) -> None:
        if self._status != MCTController.Status.RUNNING:
            raise RuntimeError("Cannot shut down if controller isn't first running.")
        for connection in self._connections.values():
            if connection.is_start_up_finished():
                connection.shut_down()

        self._status = MCTController.Status.STOPPING

        self.recording_stop()

    def supported_request_types(self) -> dict[type[MCTRequest], Callable[[dict], MCTResponse]]:
        return super().supported_request_types()

    # Right now this function doesn't update on its own - must be called externally and regularly
    async def update(
        self
    ) -> None:
        connections = list(self._connections.values())
        for connection in connections:
            await connection.update()

        if self._status == MCTController.Status.STARTING and \
           self._startup_state == MCTController.StartupState.CONNECTING:
            all_connected: bool = True
            for connection in connections:
                if self._startup_mode == StartupMode.DETECTING_ONLY and \
                   connection.get_role() == COMPONENT_ROLE_LABEL_POSE_SOLVER:
                    continue
                if not connection.is_start_up_finished():
                    all_connected = False
                    break
            if all_connected:
                self._advance_startup_state()
        elif self._status == MCTController.Status.STOPPING:
            shutdown_finished: bool = True
            for connection in connections:
                if not connection.is_shut_down():
                    shutdown_finished = False
                    break
            if shutdown_finished:
                self._status = MCTController.Status.STOPPED

        if self.is_running():
            for detector_label in self.get_active_detector_labels():
                detector_connection: DetectorConnection = self._get_connection(
                    connection_label=detector_label,
                    connection_type=DetectorConnection)
                if detector_connection is None:
                    self.status_message_source.enqueue_status_message(
                        severity="error",
                        message=f"Failed to find DetectorConnection with label {detector_label}.")
                    continue
                if detector_connection.request_id is not None:
                    _, detector_connection.request_id = self.update_request(
                        request_id=detector_connection.request_id)
                if detector_connection.request_id is None:
                    detector_connection.request_id = self.request_series_push(
                        connection_label=detector_label,
                        request_series=MCTRequestSeries(series=[DetectorFrameGetRequest()]))
            for pose_solver_label in self.get_active_pose_solver_labels():
                pose_solver_connection: PoseSolverConnection = self._get_connection(
                    connection_label=pose_solver_label,
                    connection_type=PoseSolverConnection)
                if pose_solver_connection is None:
                    self.status_message_source.enqueue_status_message(
                        severity="error",
                        message=f"Failed to find PoseSolverConnection with label {pose_solver_label}.")
                    continue
                if pose_solver_connection.request_id is not None:
                    _, pose_solver_connection.request_id = self.update_request(
                        request_id=pose_solver_connection.request_id)
                if pose_solver_connection.request_id is None:
                    solver_request_list: list[MCTRequest] = list()
                    detector_labels: list[str] = self.get_active_detector_labels()
                    for detector_label in detector_labels:
                        detector_connection: DetectorConnection = self._get_connection(
                            connection_label=detector_label,
                            connection_type=DetectorConnection)
                        current_detector_frame: DetectorFrame | None = self.get_live_detector_frame(
                            detector_label=detector_label)
                        if current_detector_frame is None:
                            continue
                        current_detector_frame_timestamp: datetime.datetime = current_detector_frame.timestamp_utc()
                        current_is_new: bool = False
                        if detector_label in pose_solver_connection.detector_timestamps:
                            old_detector_frame_timestamp = \
                                pose_solver_connection.detector_timestamps[detector_label]
                            if current_detector_frame_timestamp > old_detector_frame_timestamp:
                                current_is_new = True
                        else:
                            current_is_new = True
                        if current_is_new:
                            pose_solver_connection.detector_timestamps[detector_label] = \
                                current_detector_frame_timestamp
                            adjusted_detector_frame: DetectorFrame = current_detector_frame.copy()
                            adjusted_timestamp_utc: datetime.datetime = \
                                current_detector_frame.timestamp_utc() + \
                                datetime.timedelta(seconds=pose_solver_connection.controller_offset_seconds)
                            adjusted_detector_frame.timestamp_utc_iso8601 = adjusted_timestamp_utc.isoformat()
                            marker_request: PoseSolverAddDetectorFrameRequest = PoseSolverAddDetectorFrameRequest(
                                detector_label=detector_label,
                                detector_frame=adjusted_detector_frame)
                            solver_request_list.append(marker_request)

                            if self._recording_detector:
                                detector_connection.recording.append(current_detector_frame)
                            if self._recording_pose_solver:
                                current_pose_solver_frame = self.get_live_pose_solver_frame(pose_solver_label)
                                pose_solver_connection.recording.append(current_pose_solver_frame)

                    solver_request_list.append(PoseSolverGetPosesRequest())
                    request_series: MCTRequestSeries = MCTRequestSeries(series=solver_request_list)
                    pose_solver_connection.request_id = self.request_series_push(
                        connection_label=pose_solver_label,
                        request_series=request_series)

        if len(self._pending_request_ids) > 0:
            completed_request_ids: list[uuid.UUID] = list()
            for request_id in self._pending_request_ids:
                _, remaining_request_id = self.update_request(request_id=request_id)
                if remaining_request_id is None:
                    completed_request_ids.append(request_id)
            for request_id in completed_request_ids:
                self._pending_request_ids.remove(request_id)
            if len(self._pending_request_ids) == 0:
                self._advance_startup_state()

    def update_request(
        self,
        request_id: uuid.UUID,
        task_description: str | None = None,
        expected_response_count: int | None = None
    ) -> (bool, uuid.UUID | None):
        """
        Returns a tuple of:
        - success at handling the response (False if no response has been received)
        - value that request_id shall take for subsequent iterations (None means a response series has been received)
        """

        response_series: MCTResponseSeries | None
        _, response_series = self.response_series_pop(request_series_id=request_id)
        if response_series is None:
            return False, request_id  # try again next loop

        success: bool = self.handle_response_series(
            response_series=response_series,
            task_description=task_description,
            expected_response_count=expected_response_count)
        return success, None  # We've handled the request, request_id can be set to None
