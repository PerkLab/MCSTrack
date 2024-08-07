import numpy as np
from matplotlib import pyplot as plt
from src.board_builder.test.accuracy.structures.accuracy_test_parameters import AccuracyTestParameters as parameters


def graph_renderer(snapshots, all_collection_data, reference_to_detector_poses):
    def plot_points_3d(ax, points, colors, reference_to_detector_poses, azim=0, elev=90):
        ax.set_xlim(parameters.PLOT_X_AXIS_LIMIT)
        ax.set_ylim(parameters.PLOT_Y_AXIS_LIMIT)
        ax.set_zlim(parameters.PLOT_Z_AXIS_LIMIT)

        for color, dataset in zip(colors, points):
            for marker_points in dataset.values():  # Iterate over each marker's points
                marker_points = np.array(marker_points)

                # Calculate center point
                center = np.mean(marker_points, axis=0)

                # Calculate normal vector
                v1 = marker_points[1] - marker_points[0]
                v2 = marker_points[3] - marker_points[0]
                normal = np.cross(v1, v2)
                normal = - normal / np.linalg.norm(normal)  # Normalize the vector

                # Scale the normal vector for visualization
                scale = 20  # Adjust this value to change the length of the normal vector
                end_point = center + normal * scale

                # Draw the normal vector
                ax.quiver(center[0], center[1], center[2],
                          normal[0], normal[1], normal[2],
                          length=scale, normalize=True, color=color, arrow_length_ratio=0.1)

        for color, dataset in zip(colors, points):
            for key in dataset:
                points = dataset[key]
                x, y, z = zip(*points)
                ax.scatter(x, y, z, c=[color])

        ax.set_xlabel('X axis')
        ax.set_ylabel('Y axis')
        ax.set_zlabel('Z axis')
        ax.view_init(azim=azim, elev=elev)

        for pose in reference_to_detector_poses:
            matrix = pose.object_to_reference_matrix.as_numpy_array()
            origin = matrix[:3, 3]
            x_axis = matrix[:3, 0]
            y_axis = matrix[:3, 1]
            z_axis = matrix[:3, 2]

            scale = 50  # Adjust this to change the size of the coordinate axes

            ax.quiver(*origin, *x_axis, color='r', length=scale)
            ax.quiver(*origin, *y_axis, color='g', length=scale)
            ax.quiver(*origin, *z_axis, color='b', length=scale)

            ax.text(*(origin + x_axis * scale), pose.target_id, color='r')

    def plot_points_2d(ax_green, ax_blue, all_collection_data, colors):
        def plot_quadrilateral(ax, corners, marker_id, color):
            corners_closed = np.vstack((corners, corners[0]))
            ax.plot(corners_closed[:, 0], corners_closed[:, 1], '-', color=color)
            ax.scatter(corners[:, 0], corners[:, 1], color=color)
            center = corners.mean(axis=0)
            ax.text(center[0], center[1], f'{marker_id}', fontsize=8, ha='center', va='center', color=color)

        ax_green.set_title('Detector Green')
        ax_blue.set_title('Detector Blue')

        # Fixed width and height
        fixed_width = parameters.DETECTOR_FRAME_WIDTH
        fixed_height = parameters.DETECTOR_FRAME_HEIGHT

        detector_names = [pose.target_id for pose in parameters.DETECTOR_POSES_IN_WORLD_REFERENCE]

        # Plot points
        for i, (data, color) in enumerate(zip(all_collection_data, colors)):
            for detector, marker_snapshots in data.items():
                ax = ax_green if detector == 'detector_green' else ax_blue
                for marker_snapshot in marker_snapshots:
                    corners = np.array([(corner.x_px, corner.y_px) for corner in marker_snapshot.corner_image_points])
                    plot_quadrilateral(ax, corners, f'M{marker_snapshot.label}S{i}', color)

        # Set limits and aspect
        for ax in [ax_green, ax_blue]:
            x_center = fixed_width / 2
            y_center = fixed_height / 2
            x_min = x_center - fixed_width / 2
            x_max = x_center + fixed_width / 2
            y_min = y_center - fixed_height / 2
            y_max = y_center + fixed_height / 2

            ax.set_xlim(x_min, x_max)
            ax.set_ylim(y_max, y_min)  # Inverted y-axis
            ax.set_aspect('equal', adjustable='box')
            ax.set_xlabel('X')
            ax.set_ylabel('Y')

    # Create a figure with four subplots
    fig = plt.figure(figsize=(20, 10))
    ax1 = fig.add_subplot(221, projection='3d')
    ax2 = fig.add_subplot(222, projection='3d')
    ax3 = fig.add_subplot(223)
    ax4 = fig.add_subplot(224)

    # Define colors for each iteration
    colors = plt.cm.rainbow(np.linspace(0, 1, len(snapshots)))

    # Plot 3D points
    plot_points_3d(ax1, snapshots, colors, reference_to_detector_poses)
    plot_points_3d(ax2, snapshots, colors, reference_to_detector_poses, azim=45, elev=20)

    # Plot 2D points
    plot_points_2d(ax3, ax4, all_collection_data, colors)

    plt.tight_layout()
    plt.show()