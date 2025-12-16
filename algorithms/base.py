"""
Base class for pathfinding algorithms
"""

class PathfindingAlgorithm:
    """Base class that all pathfinding algorithms inherit from"""
    
    def __init__(self, name="Base Algorithm"):
        self.name = name
    
    def get_neighbors(self, x, y, width, height, obstacles=None):
        """Get valid neighboring coordinates (4-directional), excluding obstacles"""
        if obstacles is None:
            obstacles = set()
        
        neighbors = []
        directions = [(0, 1), (1, 0), (0, -1), (-1, 0)]  # Right, Down, Left, Up
        
        for dx, dy in directions:
            nx, ny = x + dx, y + dy
            if 0 <= nx < width and 0 <= ny < height and (nx, ny) not in obstacles:
                neighbors.append((nx, ny))
        
        return neighbors
    
    def manhattan_distance(self, point1, point2):
        """Calculate Manhattan distance between two points"""
        return abs(point1[0] - point2[0]) + abs(point1[1] - point2[1])
    
    def find_path(self, start, end, width, height):
        """
        Find path from start to end point.
        Must be implemented by subclasses.
        
        Should yield tuples of (state_type, data):
        - ('exploring', (x, y)) - currently exploring this node
        - ('visited', (x, y)) - finished exploring this node
        - ('found', path) - path found (list of coordinates)
        - ('no_path', None) - no path exists
        """
        raise NotImplementedError("Subclasses must implement find_path method")
