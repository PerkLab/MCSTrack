import asyncio
import sys
import hjson
from ipaddress import IPv4Address
import json
import logging
import numpy as np
import os
from time import sleep
from timeit import main
from scipy.spatial.transform import Rotation as R

from src.board_builder.board_builder import BoardBuilder
from src.common.structures.component_role_label import COMPONENT_ROLE_LABEL_DETECTOR, COMPONENT_ROLE_LABEL_POSE_SOLVER
from src.controller.mct_controller import MCTController
from src.controller.structures.mct_component_address import MCTComponentAddress
from src.pose_solver.util import average_quaternion, average_vector

# input_filepath = "/home/adminpi5/Documents/MCSTrack/data/measure_detector_to_reference_config.json"
if len(sys.argv) < 2:
    raise Exception("No input filepath specified")
input_filepath = sys.argv[1]

with open(input_filepath, 'r') as file:
    data = hjson.load(file)

    startup_mode = data['startup_mode']
    detectors = data['detectors']
    pose_solvers = data['pose_solvers']

controller = MCTController(
        serial_identifier="controller",
        send_status_messages_to_logger=True)

async def main():
    logging.basicConfig(level=logging.INFO)

    all_measured_transforms_by_detector = {}
    board_builder = BoardBuilder()
    detector_intrinsics = {}
    ITERATIONS = 20

    for detector in detectors:
        controller.add_connection(MCTComponentAddress(
                label=detector['label'],
                role=COMPONENT_ROLE_LABEL_DETECTOR,
                ip_address=detector['ip_address'],
                port=detector['port']
            ))
        all_measured_transforms_by_detector[detector['label']] = []

    controller.start_up()

    while controller.is_transitioning():
        await controller.update()

    for i in range(ITERATIONS):

        await controller.update()
        detectors_and_their_frames = {}

        for detector_label in controller.get_active_detector_labels():
            board_builder.pose_solver.set_intrinsic_parameters(
                detector_label, controller.get_live_detector_intrinsics(detector_label))

            frame = controller.get_live_detector_frame(detector_label)
            # Keep trying if it is a None frame, which happens on startup
            while not frame:
                await controller.update()
                frame = controller.get_live_detector_frame(detector_label)

            detectors_and_their_frames[detector_label] = frame.detected_marker_snapshots

        board_builder.locate_reference_board(detectors_and_their_frames)
    
        for idx, detector_label in enumerate(controller.get_active_detector_labels()):
            all_measured_transforms_by_detector[detector_label].append(\
                board_builder.detector_poses[idx].object_to_reference_matrix.as_numpy_array())
        sleep(0.1)

    final_matrices = {}
    for detector_label in all_measured_transforms_by_detector.keys():
        quaternions = []
        translations = []

        for matrix in all_measured_transforms_by_detector[detector_label]:
            rotation_matrix = matrix[:3,:3]
            translation = matrix[:3,3]

            quaternion = R.from_matrix(rotation_matrix).as_quat()

            quaternions.append(quaternion)
            translations.append(translation)

        avg_quaternion = average_quaternion(quaternions)
        avg_translation = average_vector(translations)

        avg_rotation_matrix = R.from_quat(avg_quaternion).as_matrix()

        avg_matrix = np.eye(4)
        avg_matrix[:3,:3] = avg_rotation_matrix
        avg_matrix[:3,3] = avg_translation

        final_matrices[detector_label] = avg_matrix
        print("Calculated detector_to_reference transform for Detector " + detector_label + ": ")
        print(avg_matrix)
        print()

        for detector in data['detectors']:
            if detector['label'] == detector_label:
                detector['fixed_transform_to_reference'] = avg_matrix.flatten().tolist()

    dir, filename = os.path.split(input_filepath)
    # Prepend filename with "output_"
    new_filename = f"output_{filename}"
    new_filepath = os.path.join(dir,new_filename)

    with open(new_filepath, 'w') as file:
        # TODO: Make this data look more clean when dumped to file
        # Also have marker corner positions as floats and not ints
        json.dump(data,file,indent=4)


if __name__ == "__main__":
    asyncio.run(main())
