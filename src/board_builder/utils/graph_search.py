from collections import deque, defaultdict
from src.board_builder.structures import PoseLocation, MatrixNode
import datetime
from src.common.structures import Matrix4x4

def create_graph(relative_pose_matrix, index_to_marker_id):
    # Create a dictionary to store all nodes by their id
    nodes = {}

    # First, create all nodes
    for index, marker_id in index_to_marker_id.items():
        nodes[marker_id] = MatrixNode(marker_id)

    # Now, establish connections between nodes
    size = len(relative_pose_matrix)
    for i in range(size):
        for j in range(size):
            if i != j and relative_pose_matrix[i][j] is not None:
                # Get the marker IDs
                node_a_id = index_to_marker_id[i]
                node_b_id = index_to_marker_id[j]

                # Get the corresponding nodes
                node_a = nodes[node_a_id]
                node_b = nodes[node_b_id]

                # Get the weight (frame_count)
                weight = relative_pose_matrix[i][j].frame_count

                # Add neighbours
                node_a.add_neighbour(node_b, weight)

    return nodes

def bfs_shortest_path(graph, root_id):
    # Dictionary to store the shortest path and the frame count to each node
    shortest_paths = {}
    # Priority queue to store (current_path_length, -total_frame_count, current_path) tuples
    queue = deque([(0, 0, [root_id])])
    # Dictionary to store visited nodes and their corresponding path lengths and frame counts
    visited = defaultdict(lambda: (float('inf'), float('-inf')))

    while queue:
        path_length, total_frame_count, path = queue.popleft()
        current_node_id = path[-1]

        # If we've already found a shorter or equally long path with a higher frame count, skip this one
        if (path_length > visited[current_node_id][0]) or \
           (path_length == visited[current_node_id][0] and -total_frame_count < visited[current_node_id][1]):
            continue

        # Update the visited dictionary with the current path's length and frame count
        visited[current_node_id] = (path_length, -total_frame_count)
        # Save the current path as the shortest path to the current node
        shortest_paths[current_node_id] = path

        # Enqueue neighbors
        current_node = graph[current_node_id]
        for neighbour in current_node.neighbours:
            if neighbour.id not in visited or (path_length + 1 <= visited[neighbour.id][0]):
                new_path = path + [neighbour.id]
                new_frame_count = total_frame_count - current_node.weights[neighbour.id]
                queue.append((path_length + 1, new_frame_count, new_path))

    return shortest_paths


def get_transform_from_root(shortest_paths, root_id, relative_pose_matrix, index_to_marker_id):
    transform_matrices = {}

    # The transform from root to root is the identity matrix
    transform_matrices[root_id] = Matrix4x4()

    for node_id, path in shortest_paths.items():
        if node_id == root_id:
            continue

        # Start with identity matrix
        transform_matrix = Matrix4x4()

        # Accumulate the transformation matrix along the path
        for i in range(len(path) - 1):
            current_node = path[i]
            next_node = path[i + 1]

            # Get the indices corresponding to the current and next node IDs
            current_index = next((idx for idx, marker_id in index_to_marker_id.items() if marker_id == current_node),
                                 None)
            next_index = next((idx for idx, marker_id in index_to_marker_id.items() if marker_id == next_node), None)

            # Get the corresponding pose location object
            pose_location = relative_pose_matrix[current_index][next_index]

            # Multiply the current transform matrix with the next one in the path
            transform_matrix = transform_matrix * Matrix4x4.from_numpy_array(pose_location.get_matrix())

        # Store the final transformation matrix for this node
        transform_matrices[node_id] = transform_matrix

    return transform_matrices

# Example relative_pose_matrix and index_to_marker_id
# Example 1
t1 = Matrix4x4(values=[
    0.90564632, -0.35969429,  0.22390513,  0.28593772,
    0.40858544,  0.87645566, -0.25484992,  0.86765748,
   -0.11241957,  0.32005842,  0.94045278,  0.49238574,
    0.        ,  0.        ,  0.        ,  1.        ]).as_numpy_array()

# Example 2
t2 = Matrix4x4(values=[
    0.74483241,  0.36442377, -0.55804099,  0.38474381,
   -0.38669273,  0.92000765,  0.05812109,  0.68349235,
    0.5438679 ,  0.14482633,  0.82673116,  0.39245715,
    0.        ,  0.        ,  0.        ,  1.        ]).as_numpy_array()

# Example 3
t3 = Matrix4x4(values=[
    0.71627787, -0.59243734,  0.36872095,  0.09341843,
    0.65127302,  0.75701292,  0.04740327,  0.46390599,
   -0.24806341,  0.27605793,  0.92824342,  0.02546277,
    0.        ,  0.        ,  0.        ,  1.        ]).as_numpy_array()

# Example 4
t4 = Matrix4x4(values=[
    0.19197563,  0.7921565 , -0.57822617,  0.82934556,
   -0.80821986,  0.48546982,  0.33340147,  0.39673983,
    0.55656374,  0.36924802,  0.74429393,  0.51463816,
    0.        ,  0.        ,  0.        ,  1.        ]).as_numpy_array()

# Example 5
t5 = Matrix4x4(values=[
    0.11359723,  0.81994285,  0.56134747,  0.72938457,
    0.78432915, -0.42265346,  0.45456387,  0.24173855,
    0.60988858,  0.38607418, -0.69282023,  0.41689203,
    0.        ,  0.        ,  0.        ,  1.        ]).as_numpy_array()


timestamp = str(datetime.datetime.utcnow())

poseLocation_01 = PoseLocation("01")
poseLocation_01.frame_count += 60
poseLocation_01.add_matrix(t1, timestamp)

poseLocation_02 = PoseLocation("02")
poseLocation_02.frame_count += 71
poseLocation_02.add_matrix(t2, timestamp)

poseLocation_13 = PoseLocation("13")
poseLocation_13.frame_count += 59
poseLocation_13.add_matrix(t3, timestamp)

poseLocation_23 = PoseLocation("23")
poseLocation_23.frame_count += 61
poseLocation_23.add_matrix(t4, timestamp)

poseLocation_10 = PoseLocation("10")
poseLocation_10.frame_count += 1
poseLocation_10.add_matrix(t5, timestamp)

relative_pose_matrix = [
    [None, poseLocation_01, poseLocation_02, None],
    [poseLocation_10, None, None, poseLocation_13],
    [None, None, None, poseLocation_23],
    [None, None, None, None]
]

index_to_marker_id = {
    0: "0",
    1: "1",
    2: "2",
    3: "3"
}

# Create the graph
graph = create_graph(relative_pose_matrix, index_to_marker_id)

# Perform BFS to find the shortest path from the root node (Node "0")
root_id = "0"
shortest_paths = bfs_shortest_path(graph, root_id)

# Print the shortest paths
print(f"Shortest paths from Node {root_id}:")
for node_id, path in shortest_paths.items():
    print(f" - To Node {node_id}: {' -> '.join(path)}")

# Compute the transformation matrices from the root to each node
transform_matrices = get_transform_from_root(shortest_paths, root_id, relative_pose_matrix, index_to_marker_id)

# Print the resulting transformation matrices
for node_id, matrix in transform_matrices.items():
    print(f"Transform from {root_id} to {node_id}:")
    print(matrix.as_numpy_array())
