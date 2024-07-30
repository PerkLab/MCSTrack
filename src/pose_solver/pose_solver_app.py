from .api import \
    PoseSolverAddDetectorFrameRequest, \
    PoseSolverAddTargetMarkerRequest, \
    PoseSolverGetPosesResponse, \
    PoseSolverSetIntrinsicRequest
from .pose_solver import \
    PoseSolver
from .pose_solver_api import \
    PoseSolverAPI
from .structures import \
    PoseSolverConfiguration
from src.common import \
    EmptyResponse, \
    ErrorResponse
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.websockets import WebSocket
from fastapi_utils.tasks import repeat_every
import hjson
import logging
import os


logger = logging.getLogger(__name__)
pose_solver = PoseSolver()


def create_app() -> FastAPI:
    configuration_filepath: str = os.path.join(
        os.path.dirname(__file__), "..", "..", "data", "pose_solver_config.json")
    configuration: PoseSolverConfiguration
    with open(configuration_filepath, 'r') as infile:
        file_contents: str = infile.read()
        configuration_dict = hjson.loads(file_contents)
        configuration = PoseSolverConfiguration(**configuration_dict)
    pose_solver_api = PoseSolverAPI(
        configuration=configuration,
        pose_solver=pose_solver)
    pose_solver_app = FastAPI()

    # CORS Middleware
    origins = ["http://localhost"]
    pose_solver_app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"])

    @pose_solver_app.post("/add_detector_frame")
    async def add_marker_corners(
        request: PoseSolverAddDetectorFrameRequest
    ) -> EmptyResponse | ErrorResponse:
        return pose_solver_api.add_detector_frame(request=request)

    @pose_solver_app.post("/add_target")
    async def add_target_marker(
        request: PoseSolverAddTargetMarkerRequest
    ) -> EmptyResponse | ErrorResponse:
        return pose_solver_api.add_target(request=request)

    @pose_solver_app.get("/get_poses")
    async def get_poses() -> PoseSolverGetPosesResponse | ErrorResponse:
        return pose_solver_api.get_poses()

    @pose_solver_app.post("/set_intrinsic_parameters")
    async def set_intrinsic_parameters(
        request: PoseSolverSetIntrinsicRequest
    ) -> EmptyResponse | ErrorResponse:
        return pose_solver_api.set_intrinsic_parameters(request=request)

    @pose_solver_app.head("/start_capture")
    async def start_capture() -> None:
        pose_solver_api.start_pose_solver()

    @pose_solver_app.head("/stop_capture")
    async def stop_capture() -> None:
        pose_solver_api.stop_pose_solver()

    @pose_solver_app.websocket("/websocket")
    async def websocket_handler(websocket: WebSocket) -> None:
        await pose_solver_api.websocket_handler(websocket=websocket)

    @pose_solver_app.on_event("startup")
    @repeat_every(seconds=0.001)
    async def internal_update() -> None:
        await pose_solver_api.update()

    return pose_solver_app


app = create_app()
