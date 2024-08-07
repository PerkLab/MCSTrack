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
    SCENE_NAME = 'cube'  # Name of the board definition (two_markers, cube, planar)
    SCENE_GENERATION_X_BOUNDS = (100, 400)
    SCENE_GENERATION_Y_BOUNDS = (-100, 100)
    SCENE_GENERATION_Z_BOUNDS = (0, 150)
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
            target_id='detector_green',
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
            target_id='detector_blue',
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

    # TODO: The values were taken from lab.
    DETECTOR_POSES_OBJECT_TO_REFERENCE = [
        Pose(
            target_id='detector_green',
            object_to_reference_matrix=Matrix4x4(
                values=[
                    -0.06426231056361736, 0.5706306814489908, -0.8186885737752091, -151.62741907631478,
                    -0.994648766593041, 0.029878321747323022, 0.0988995298497714, 47.46624296855151,
                    0.08089614673127254, 0.8206630924311293, 0.5656570534921389, 277.58065572599085,
                    0.0, 0.0, 0.0, 1.0
                ]
            ),
            solver_timestamp_utc_iso8601='2024-07-04 10:15:21.067737'
        ),
        Pose(
            target_id='detector_blue',
            object_to_reference_matrix=Matrix4x4(
                values=[
                    0.04812050411931307, -0.5726874406724359, 0.8183602583088689, 652.57542317708334,
                    0.9988407221518759, 0.026543078438890644, -0.04015814684601582, -20.15293969048395,
                    0.0012762658118295467, 0.8193439816603538, 0.5733008031239233, 284.4946346706814,
                    0.0, 0.0, 0.0, 1.0
                ]
            ),
            solver_timestamp_utc_iso8601='2024-07-04 10:15:21.067737'
        )
    ]

    DETECTOR_INTRINSICS = IntrinsicParameters(
        focal_length_x_px=600.,
        focal_length_y_px=600.,
        optical_center_x_px=int(DETECTOR_FRAME_WIDTH / 2),
        optical_center_y_px=int(DETECTOR_FRAME_HEIGHT / 2),
        radial_distortion_coefficients=[0., 0., 0.],
        tangential_distortion_coefficients=[0., 0.]
    )
