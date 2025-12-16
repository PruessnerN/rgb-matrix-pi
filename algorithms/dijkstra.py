"""
Dijkstra's Algorithm
Finds shortest path considering edge weights (all edges weight 1 in our case)
Similar to BFS for unweighted graphs
"""

import heapq
from .base import PathfindingAlgorithm


class DijkstraAlgorithm(PathfindingAlgorithm):
    def __init__(self):
        super().__init__("Dijkstra's Algorithm")
    
    def find_path(self, start, end, width, height, obstacles=None):
        """
        Dijkstra's pathfinding algorithm
        Uses priority queue to explore lowest-cost nodes first
        """
        if obstacles is None:
            obstacles = set()
        # Priority queue: (cost, node)
        pq = [(0, start)]
        visited = set()
        parent = {start: None}
        cost = {start: 0}
        
        while pq:
            current_cost, current = heapq.heappop(pq)
            
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
                    new_cost = current_cost + 1  # All edges have cost 1
                    
                    if neighbor not in cost or new_cost < cost[neighbor]:
                        cost[neighbor] = new_cost
                        parent[neighbor] = current
                        heapq.heappush(pq, (new_cost, neighbor))
        
        # No path found
        yield ('no_path', None)
