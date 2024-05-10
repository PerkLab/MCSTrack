import numpy as np

from src.common.structures import Matrix4x4, Pose, IntrinsicParameters


class AccuracyTestParameters:

    # Noise
    ACCURACY_PERCENTAGE = 95.44  # Percentage of data within two standard deviations
    NOISE_LEVEL = 2  # Max noise level of corner data within two standard deviations
    HIGH_NOISE_LEVEL = 1.5  # Multiplier for noise level of corner data outside two standard deviations

    # Scene generation
    BOARD_MARKER_SIZE = 10  # Size of the markers in mm
    NUMBER_OF_SNAPSHOTS = 10  # Number of scenes generated for the collection of data
    SCENE_GENERATION_X_BOUNDS = (200, 300)  # (200, 300)
    SCENE_GENERATION_Y_BOUNDS = (-50, 50)  # (-50, 50)
    SCENE_GENERATION_Z_BOUNDS = (0, 100)  # (0, 100)
    SCENE_GENERATION_ROTATION_LIMIT = 30  # Amount of degrees a marker can rotate from its original definition

    # Plotting
    PLOT_X_AXIS_LIMIT = [0, 500]
    PLOT_Y_AXIS_LIMIT = [-250, 250]
    PLOT_Z_AXIS_LIMIT = [0, 500]

    # Detector setup and intrinsics
    DETECTOR_FRAME_WIDTH = 640
    DETECTOR_FRAME_HEIGHT = 480
    DETECTOR_POSES_IN_WORLD_REFERENCE = [
        Pose(
            target_id='camera 1',
            object_to_reference_matrix=Matrix4x4(
                values=[
                    0.0, -float(np.sqrt(2)) / 2, float(np.sqrt(2)) / 2, 0.0,
                    -1.0, 0.0, 0.0, 0.0,
                    0.0, -float(np.sqrt(2)) / 2, -float(np.sqrt(2)) / 2, 250.0,
                    0.0, 0.0, 0.0, 1.0
                ]
            ),
            solver_timestamp_utc_iso8601='2024-07-04 10:15:21.067737'
        ),
        Pose(
            target_id='camera 2',
            object_to_reference_matrix=Matrix4x4(
                values=[
                    0.0, float(np.sqrt(2)) / 2, -float(np.sqrt(2)) / 2, 500.0,
                    1.0, 0.0, 0.0, 0.0,
                    0.0, -float(np.sqrt(2)) / 2, -float(np.sqrt(2)) / 2, 250.0,
                    0.0, 0.0, 0.0, 1.0
                ]
            ),
            solver_timestamp_utc_iso8601='2024-07-04 10:15:21.067737'
        )
    ]

    DETECTOR_INTRINSICS = IntrinsicParameters(
        focal_length_x_px=879.19,
        focal_length_y_px=895.69,
        optical_center_x_px=int(DETECTOR_FRAME_WIDTH / 2),
        optical_center_y_px=int(DETECTOR_FRAME_HEIGHT / 2),
        radial_distortion_coefficients=[0., 0., 0.],
        tangential_distortion_coefficients=[0., 0.]
    )
