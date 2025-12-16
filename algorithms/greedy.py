"""
Greedy Best-First Search
Always moves toward the goal using heuristic, ignoring actual distance traveled
Faster than A* but doesn't guarantee shortest path - can get stuck going around obstacles
Creates a very direct, "eager" exploration pattern
"""

import heapq
from .base import PathfindingAlgorithm


class GreedyBestFirstAlgorithm(PathfindingAlgorithm):
    def __init__(self):
        super().__init__("Greedy Best-First Search")
    
    def find_path(self, start, end, width, height, obstacles=None):
        """
        Greedy Best-First Search
        Uses only heuristic (h) to guide search, ignoring actual cost (g)
        Visual effect: Very focused "beeline" toward target
        """
        if obstacles is None:
            obstacles = set()
        # Priority queue: (heuristic, node)
        pq = [(0, start)]
        visited = set()
        parent = {start: None}
        
        while pq:
            _, current = heapq.heappop(pq)
            
            if current in visited:
                continue
            
            visited.add(current)
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
            
            yield ('visited', current)
            
            # Explore neighbors
            for neighbor in self.get_neighbors(*current, width, height, obstacles):
                if neighbor not in visited:
                    # Only use heuristic, ignore actual cost
                    h_score = self.manhattan_distance(neighbor, end)
                    parent[neighbor] = current
                    heapq.heappush(pq, (h_score, neighbor))
        
        yield ('no_path', None)
