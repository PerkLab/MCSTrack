class MatrixNode:
    def __init__(self, node_id: str):
        self.id = node_id
        self.neighbours = []
        self.weights = {}

    def add_neighbour(self, neighbour_node, weight: int):
        self.neighbours.append(neighbour_node)
        self.weights[neighbour_node.id] = weight
