"""
A* (A-Star) Algorithm
Finds shortest path using heuristic (Manhattan distance) to guide search
More efficient than Dijkstra for pathfinding with known goal
"""

import heapq
from .base import PathfindingAlgorithm


class AStarAlgorithm(PathfindingAlgorithm):
    def __init__(self):
        super().__init__("A* (A-Star)")
    
    def find_path(self, start, end, width, height, obstacles=None):
        """
        A* pathfinding algorithm
        Uses f(n) = g(n) + h(n) where:
        - g(n) = cost from start to n
        - h(n) = heuristic estimate from n to goal (Manhattan distance)
        """
        if obstacles is None:
            obstacles = set()
        # Priority queue: (f_score, g_score, node)
        # Include g_score as tiebreaker for consistent ordering
        pq = [(0, 0, start)]
        visited = set()
        parent = {start: None}
        g_score = {start: 0}
        
        while pq:
            _, current_g, current = heapq.heappop(pq)
            
            # Skip if already visited
            if current in visited:
                continue
            
            visited.add(current)
            
            # Yield current state for visualization
            yield ('exploring', current)
            
            # Check if we reached the end
            if current == end:
                # Reconstruct path
                path = []
                node = end
                while node is not None:
                    path.append(node)
                    node = parent[node]
                path.reverse()
                yield ('found', path)
                return
            
            # Mark as visited
            yield ('visited', current)
            
            # Explore neighbors
            for neighbor in self.get_neighbors(*current, width, height, obstacles):
                if neighbor not in visited:
                    tentative_g = current_g + 1  # All edges have cost 1
                    
                    if neighbor not in g_score or tentative_g < g_score[neighbor]:
                        g_score[neighbor] = tentative_g
                        h_score = self.manhattan_distance(neighbor, end)
                        f_score = tentative_g + h_score
                        parent[neighbor] = current
                        heapq.heappush(pq, (f_score, tentative_g, neighbor))
        
        # No path found
        yield ('no_path', None)
