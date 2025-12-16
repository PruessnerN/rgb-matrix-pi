"""
Random Walk / Drunkard's Walk
Completely random pathfinding - eventually finds target by pure chance
Creates chaotic, unpredictable patterns - more entertainment than efficiency!
"""

import random
from .base import PathfindingAlgorithm


class RandomWalkAlgorithm(PathfindingAlgorithm):
    def __init__(self):
        super().__init__("Random Walk (Drunkard)")
    
    def find_path(self, start, end, width, height, obstacles=None):
        """
        Random walk pathfinding
        Visual effect: Chaotic wandering until it stumbles onto the goal
        Then shows the shortest path instead of the wandering trail
        """
        if obstacles is None:
            obstacles = set()
        current = start
        visited = set()
        parent = {start: None}
        max_steps = width * height * 2  # Prevent infinite loops
        
        for step in range(max_steps):
            yield ('exploring', current)
            
            # Check if we reached the end
            if current == end:
                # Reconstruct shortest path using parent chain
                path = []
                node = end
                while node is not None:
                    path.append(node)
                    node = parent[node]
                path.reverse()
                yield ('found', path)
                return
            
            yield ('visited', current)
            visited.add(current)
            
            # Get neighbors and pick one randomly
            neighbors = self.get_neighbors(*current, width, height, obstacles)
            
            # Prefer unvisited neighbors, but occasionally revisit
            unvisited = [n for n in neighbors if n not in visited]
            
            if unvisited and random.random() > 0.3:  # 70% chance to go to unvisited
                next_node = random.choice(unvisited)
            else:
                next_node = random.choice(neighbors)  # Random including visited
            
            # Track parent for shortest path reconstruction
            if next_node not in parent:
                parent[next_node] = current
            
            current = next_node
        
        # Couldn't find path in reasonable time
        yield ('no_path', None)
