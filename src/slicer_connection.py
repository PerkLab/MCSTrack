import asyncio
import sys
import hjson
import numpy as np
import pyigtl
import time as t
import logging

from src.common.api.mct_request_series import MCTRequestSeries
from src.common.structures.component_role_label import COMPONENT_ROLE_LABEL_DETECTOR, COMPONENT_ROLE_LABEL_POSE_SOLVER
from src.common.structures.target import TargetBase
from src.controller.mct_controller import MCTController
from src.controller.structures.mct_component_address import MCTComponentAddress
from ipaddress import IPv4Address

from src.pose_solver.api import PoseSolverAddTargetMarkerRequest
from src.pose_solver.api import TargetMarker
from src.pose_solver.api import PoseSolverSetReferenceRequest

from src.controller.structures.connection import Connection

# Input filepath is specified by command line arguments
if len(sys.argv) < 2:
    raise Exception("No input filepath specified")
input_filepath = sys.argv[1]

with open(input_filepath, 'r') as file:
    data = hjson.load(file)

server = pyigtl.OpenIGTLinkServer(port=18944,local_server=False)

async def update(controller,pose_solver_label):
    try:
        await controller.update()

        ps_frame = controller.get_live_pose_solver_frame(pose_solver_label)
        timestamp = ps_frame.timestamp_utc_iso8601

        if len(ps_frame.target_poses) > 0:
            target_poses = ps_frame.target_poses[0]
            message = pyigtl.TransformMessage(
                matrix=target_poses.object_to_reference_matrix.as_numpy_array(),
                # timestamp=target_poses.solver_timestamp_utc_iso8601,
                device_name=target_poses.target_id
            )
            server.send_message(message,wait=True)
    except Exception as e:
        controller.add_status_message(
            severity="error",
            message=f"Exception occurred in controller loop: {str(e)}")
        
    event_loop: asyncio.AbstractEventLoop = asyncio.get_running_loop()
    event_loop.create_task(update(controller,pose_solver_label))

async def main():
    logging.basicConfig(level=logging.INFO)

    controller = MCTController(
        serial_identifier="controller",
        send_status_messages_to_logger=True)
    
    controller.add_status_message(
            severity="info",
            message=f"Slicer client connected")

    controller.start_from_configuration_filepath(input_filepath)

    while controller.is_transitioning():
        await controller.update()

    event_loop: asyncio.AbstractEventLoop = asyncio.get_running_loop()
    event_loop.create_task(update(controller=controller, pose_solver_label="sol"))

    while True:
        await asyncio.sleep(1)

if __name__ == "__main__":
    while not server.is_connected():
        t.sleep(0.1)

    asyncio.run(main())
    