from collections import deque, defaultdict
from typing import Dict, List, Tuple

from src.board_builder.structures import MatrixNode, PoseLocation
from src.common.structures import Matrix4x4

def create_graph(
    relative_pose_matrix: List[List[PoseLocation | None]],
    index_to_marker_id: Dict[int, str]
) -> Dict[str, MatrixNode]:
    # Create a dictionary to store all nodes by their id
    nodes: Dict[str, MatrixNode] = {}

    # Create all the nodes
    for index, marker_id in index_to_marker_id.items():
        nodes[marker_id] = MatrixNode(marker_id)

    # Connect all the nodes
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

def bfs_shortest_path(
    graph: Dict[str, MatrixNode],
    root_id: str
) -> Dict[str, List[str]]:
    # Dictionary to store the shortest path and the frame count to each node
    shortest_paths: Dict[str, List[str]] = {}
    # Priority queue to store (current_path_length, -total_frame_count, current_path) tuples
    queue: deque[Tuple[int, int, List[str]]] = deque([(0, 0, [root_id])])
    # Dictionary to store visited nodes and their corresponding path lengths and frame counts
    visited: Dict[str, Tuple[int, int]] = defaultdict(lambda: (float('inf'), float('-inf')))

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

def get_transform_from_root(
    shortest_paths: Dict[str, List[str]],
    root_id: str,
    relative_pose_matrix: List[List[PoseLocation | None]],
    index_to_marker_id: Dict[int, str]
) -> Dict[str, Matrix4x4]:
    transform_matrices: Dict[str, Matrix4x4] = {}

    # The transform from root to root is the identity matrix
    transform_matrices[root_id] = Matrix4x4()

    for node_id, path in shortest_paths.items():
        if node_id == root_id:
            continue

        transform_matrix = Matrix4x4()
        for i in range(len(path) - 1):
            current_node = path[i]
            next_node = path[i + 1]

            current_index = next((idx for idx, marker_id in index_to_marker_id.items() if marker_id == current_node),
                                 None)
            next_index = next((idx for idx, marker_id in index_to_marker_id.items() if marker_id == next_node), None)

            pose_location = relative_pose_matrix[current_index][next_index]
            transform_matrix = transform_matrix * Matrix4x4.from_numpy_array(pose_location.get_matrix())

        transform_matrices[node_id] = transform_matrix

    return transform_matrices
