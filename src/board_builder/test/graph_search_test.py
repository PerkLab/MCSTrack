from src.board_builder.structures import PoseLocation
import datetime
from src.common.structures import Matrix4x4
from src.board_builder.utils.graph_search import create_graph, bfs_shortest_path, get_transform_from_root

"""
Description: Test case for the BFS/graph_search algorithm
"""

# Example relative_pose_matrix and index_to_marker_id
# Example 1
t1 = Matrix4x4(values=[
    1.0, 0.0, 0.0, 20.0,
    0.0, 1.0, 0.0, 0.0 ,
    0.0, 0.0, 1.0, 0.0 ,
    0.0, 0.0, 0.0, 1.0
]).as_numpy_array()


# Example 2
t2 = Matrix4x4(values=[
    1.0, 0.0, 0.0, 10.0,
    0.0, 1.0, 0.0, 20.0 ,
    0.0, 0.0, 1.0, 0.0 ,
    0.0, 0.0, 0.0, 1.0
]).as_numpy_array()

# Example 3
t3 = Matrix4x4(values=[
    0.71627787, -0.59243734,  0.36872095,  0.09341843,
    0.65127302,  0.75701292,  0.04740327,  0.46390599,
   -0.24806341,  0.27605793,  0.92824342,  0.02546277,
    0.        ,  0.        ,  0.        ,  1.
]).as_numpy_array()

# Example 4
t4 = Matrix4x4(values=[
    1.0, 0.0, 0.0, 10.0,
    0.0, 1.0, 0.0, 0.0 ,
    0.0, 0.0, 1.0, 0.0 ,
    0.0, 0.0, 0.0, 1.0
]).as_numpy_array()

# Example 5
t5 = Matrix4x4(values=[
    0.11359723,  0.81994285,  0.56134747,  0.72938457,
    0.78432915, -0.42265346,  0.45456387,  0.24173855,
    0.60988858,  0.38607418, -0.69282023,  0.41689203,
    0.        ,  0.        ,  0.        ,  1.
]).as_numpy_array()


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
