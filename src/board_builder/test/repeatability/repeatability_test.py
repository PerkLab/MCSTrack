import json
import os
import numpy as np


def compute_mean_corners(json_file):
    with open(json_file, 'r') as file:
        data = json.load(file)

    # Initialize a dictionary to store the sum and count for each marker's corners
    corner_sums = {}
    corner_counts = {}

    # Iterate through each run in the data
    for run in data:
        for marker_id, corners in run.items():
            if marker_id not in corner_sums:
                # Initialize sums and counts for this marker
                corner_sums[marker_id] = np.zeros((4, 3))
                corner_counts[marker_id] = 0

            # Add the current corners to the sum
            corner_sums[marker_id] += np.array(corners)
            corner_counts[marker_id] += 1

    # Compute the mean for each marker's corners
    mean_corners = {}
    for marker_id, sums in corner_sums.items():
        mean_corners[marker_id] = (sums / corner_counts[marker_id]).tolist()

    return mean_corners, data


def compute_distances_to_mean(data, mean_corners):
    distances = []

    for run in data:
        for marker_id, corners in run.items():
            mean_corners_marker = np.array(mean_corners[marker_id])
            for i, corner in enumerate(corners):
                distance = np.linalg.norm(np.array(corner) - mean_corners_marker[i])
                distances.append(distance)

    mean_distance = np.mean(distances)
    std_distance = np.std(distances)

    return mean_distance, std_distance


if __name__ == "__main__":
    script_dir = os.path.dirname(os.path.abspath(__file__))
    script_name = 'top_data.json'  # top_data.json, planar_data.json
    input_file = os.path.join(script_dir, 'planar_data.json')

    mean_corners, data = compute_mean_corners(input_file)
    mean_distance, std_distance = compute_distances_to_mean(data, mean_corners)

    # Print the results
    print("Mean Corners:")
    print(json.dumps(mean_corners, indent=4))
    print(f"Total Mean Distance to Theoretical Values: {mean_distance}")
    print(f"Standard Deviation of Distances: {std_distance}")
