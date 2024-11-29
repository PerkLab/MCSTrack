from src.common import \
    MCTRequest, \
    MCTResponse
from src.common.structures import \
    DetectorFrame, \
    IntrinsicParameters, \
    Matrix4x4, \
    Pose, \
    TargetBoard, \
    TargetMarker
from pydantic import Field
from typing import Final, Literal, Union


class PoseSolverAddDetectorFrameRequest(MCTRequest):
    _TYPE_IDENTIFIER: Final[str] = "add_marker_corners"

    @staticmethod
    def parsable_type_identifier() -> str:
        return PoseSolverAddDetectorFrameRequest._TYPE_IDENTIFIER

    # noinspection PyTypeHints
    parsable_type: Literal[_TYPE_IDENTIFIER] = Field(default=_TYPE_IDENTIFIER)

    detector_label: str = Field()
    detector_frame: DetectorFrame = Field()


class PoseSolverAddTargetMarkerRequest(MCTRequest):
    _TYPE_IDENTIFIER: Final[str] = "add_target_marker"

    @staticmethod
    def parsable_type_identifier() -> str:
        return PoseSolverAddTargetMarkerRequest._TYPE_IDENTIFIER

    # noinspection PyTypeHints
    parsable_type: Literal[_TYPE_IDENTIFIER] = Field(default=_TYPE_IDENTIFIER)

    target: TargetMarker = Field()


class PoseSolverAddTargetBoardRequest(MCTRequest):
    _TYPE_IDENTIFIER: Final[str] = "add_target_board"

    @staticmethod
    def parsable_type_identifier() -> str:
        return PoseSolverAddTargetBoardRequest._TYPE_IDENTIFIER

    # noinspection PyTypeHints
    parsable_type: Literal[_TYPE_IDENTIFIER] = Field(default=_TYPE_IDENTIFIER)

    target: TargetBoard = Field()


class PoseSolverAddTargetResponse(MCTResponse):
    _TYPE_IDENTIFIER: Final[str] = "add_marker_corners"

    @staticmethod
    def parsable_type_identifier() -> str:
        return PoseSolverAddTargetResponse._TYPE_IDENTIFIER

    # noinspection PyTypeHints
    parsable_type: Literal[_TYPE_IDENTIFIER] = Field(default=_TYPE_IDENTIFIER)

    target_id: str = Field()


class PoseSolverGetPosesRequest(MCTRequest):
    _TYPE_IDENTIFIER: Final[str] = "get_poses"

    @staticmethod
    def parsable_type_identifier() -> str:
        return PoseSolverGetPosesRequest._TYPE_IDENTIFIER

    # noinspection PyTypeHints
    parsable_type: Literal[_TYPE_IDENTIFIER] = Field(default=_TYPE_IDENTIFIER)


class PoseSolverGetPosesResponse(MCTResponse):
    _TYPE_IDENTIFIER: Final[str] = "get_poses"

    @staticmethod
    def parsable_type_identifier() -> str:
        return PoseSolverGetPosesResponse._TYPE_IDENTIFIER

    # noinspection PyTypeHints
    parsable_type: Literal[_TYPE_IDENTIFIER] = Field(default=_TYPE_IDENTIFIER)

    detector_poses: list[Pose]
    target_poses: list[Pose]


class PoseSolverSetExtrinsicRequest(MCTRequest):
    _TYPE_IDENTIFIER: Final[str] = "set_extrinsic_parameters"

    @staticmethod
    def parsable_type_identifier() -> str:
        return PoseSolverSetExtrinsicRequest._TYPE_IDENTIFIER

    # noinspection PyTypeHints
    parsable_type: Literal[_TYPE_IDENTIFIER] = Field(default=_TYPE_IDENTIFIER)

    detector_label: str = Field()
    transform_to_reference: Matrix4x4 = Field()


class PoseSolverSetIntrinsicRequest(MCTRequest):
    _TYPE_IDENTIFIER: Final[str] = "set_intrinsic_parameters"

    @staticmethod
    def parsable_type_identifier() -> str:
        return PoseSolverSetIntrinsicRequest._TYPE_IDENTIFIER

    # noinspection PyTypeHints
    parsable_type: Literal[_TYPE_IDENTIFIER] = Field(default=_TYPE_IDENTIFIER)

    detector_label: str = Field()
    intrinsic_parameters: IntrinsicParameters = Field()


class PoseSolverSetReferenceRequest(MCTRequest):
    _TYPE_IDENTIFIER: Final[str] = "set_reference_marker"

    @staticmethod
    def parsable_type_identifier() -> str:
        return PoseSolverSetReferenceRequest._TYPE_IDENTIFIER

    # noinspection PyTypeHints
    parsable_type: Literal[_TYPE_IDENTIFIER] = Field(default=_TYPE_IDENTIFIER)

    marker_id: int = Field()
    marker_diameter: float = Field()


class PoseSolverSetTargetsRequest(MCTRequest):
    _TYPE_IDENTIFIER: Final[str] = "set_targets"

    @staticmethod
    def parsable_type_identifier() -> str:
        return PoseSolverSetTargetsRequest._TYPE_IDENTIFIER

    # noinspection PyTypeHints
    parsable_type: Literal[_TYPE_IDENTIFIER] = Field(default=_TYPE_IDENTIFIER)

    targets: list[Union[TargetMarker, TargetBoard]] = Field()


class PoseSolverStartRequest(MCTRequest):
    _TYPE_IDENTIFIER: Final[str] = "start_pose_solver"

    @staticmethod
    def parsable_type_identifier() -> str:
        return PoseSolverStartRequest._TYPE_IDENTIFIER

    # noinspection PyTypeHints
    parsable_type: Literal[_TYPE_IDENTIFIER] = Field(default=_TYPE_IDENTIFIER)


class PoseSolverStopRequest(MCTRequest):
    _TYPE_IDENTIFIER: Final[str] = "stop_pose_solver"

    @staticmethod
    def parsable_type_identifier() -> str:
        return PoseSolverStopRequest._TYPE_IDENTIFIER

    # noinspection PyTypeHints
    parsable_type: Literal[_TYPE_IDENTIFIER] = Field(default=_TYPE_IDENTIFIER)
