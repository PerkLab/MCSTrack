from cv2 import aruco

from src.pose_solver.pose_solver import \
    ImagePointSetsKey, \
    MarkerKey, \
    CornerSetReference, \
    TargetDepthKey, \
    TargetDepth, \
    PoseExtrapolationQuality, \
    PoseSolver

from src.pose_solver.structures import \
    MarkerCorners, \
    TargetMarker, \
    Target

from src.common.structures import \
    IntrinsicParameters \

import cv2
import cv2.aruco
import datetime
import numpy
from scipy.spatial.transform import Rotation
from typing import Callable, Final, Optional, TypeVar
import uuid



REFERENCE_MARKER_ID: Final[int] = 0
TARGET_MARKER_ID: Final[int] = 1
MARKER_SIZE_MM: Final[float] = 10.0
DETECTOR_GREEN_NAME: Final[str] = "default_camera"
DETECTOR_GREEN_INTRINSICS: Final[IntrinsicParameters] = IntrinsicParameters(
    focal_length_x_px=629.7257712407858,
    focal_length_y_px=631.1144336572407,
    optical_center_x_px=327.78473901724755,
    optical_center_y_px=226.74054836282653,
    radial_distortion_coefficients=[
        0.05560270909494751,
        -0.28733139601291297,
        1.182627063988894],
    tangential_distortion_coefficients=[
        -0.00454124371092251,
        0.0009635939551320261])


# target_marker = pose_solver.add_target_marker(marker_id=TARGET_MARKER_ID, marker_diameter=)
marker_corners_dict = {}
target_markers_list = []

def detect_aruco_from_camera(pose_solver):

    ### OPENCV SETUP ###
    cap = cv2.VideoCapture(1)  # Camera 1 for David's computer

    if not cap.isOpened():
        print("Cannot open camera")
        exit()

    aruco_dict = aruco.Dictionary_get(aruco.DICT_4X4_100)
    parameters = aruco.DetectorParameters_create()

    while True:

        ret, frame = cap.read()
        if not ret:
            print("Can't receive frame (stream end?). Exiting ...")
            break

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)


        ### DETECTING CORNERS ###
        corners, ids, rejectedImgPoints = aruco.detectMarkers(gray, aruco_dict, parameters=parameters)

        if ids is not None:
            aruco.drawDetectedMarkers(frame, corners, ids)

            ### ADD TARGET MARKER ###
            for marker_id in range(len(ids)):
                if ids[marker_id][0] not in target_markers_list and ids[marker_id] != REFERENCE_MARKER_ID:
                    target_markers_list.append(ids[marker_id][0])
                    target_marker_diameter = MARKER_SIZE_MM
                    if not pose_solver.target_marker_exists(ids[marker_id][0], MARKER_SIZE_MM):
                        pose_solver.add_target_marker(marker_id=marker_id, marker_diameter=target_marker_diameter)

            ### ADD MARKER CORNERS ###
            for i, corner in enumerate(corners):
                marker_corners = MarkerCorners(
                    detector_label='default_camera',
                    marker_id=int(ids[i][0]),
                    points=corner[0].tolist(),
                    timestamp=datetime.datetime.now()
                )
                pose_solver.add_marker_corners([marker_corners])

                marker_corners_dict[int(ids[i][0])] = corner[0].tolist()
                #print(marker_corners_dict)

                ### DRAWING VECTORS ###
                """
                if len(marker_corners_dict) > 1:
                    first_marker_id = list(marker_corners_dict.keys())[0]
                    first_marker_topleft_corner = marker_corners_dict[first_marker_id][0]

                    for key, value in marker_corners_dict.items():
                        if key != first_marker_id:
                            topleft_corner = value[0]
                            cv2.line(frame, tuple(map(int, first_marker_topleft_corner)),
                                     tuple(map(int, topleft_corner)), (0, 255, 0), 2)
                """


        # Display the resulting frame
        cv2.imshow('Frame with ArUco markers', frame)

        # Press 'q' to exit
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    # When everything done, release the capture
    cap.release()
    cv2.destroyAllWindows()

    # GET POSES
    detector_poses, target_poses = pose_solver.get_poses()
    print("Detector Poses:", detector_poses)
    print("Target Poses:", target_poses)

pose_solver = PoseSolver()

### SET INTRINSIC PARAMETERS ###
pose_solver.set_intrinsic_parameters(DETECTOR_GREEN_NAME, DETECTOR_GREEN_INTRINSICS)

### SET REFERENCE TARGET ###
reference_target: Target = TargetMarker(
            marker_id=REFERENCE_MARKER_ID,
            marker_size=MARKER_SIZE_MM)
pose_solver.set_reference_target(reference_target)

detect_aruco_from_camera(pose_solver)

print("Target Marker List:", target_markers_list)
