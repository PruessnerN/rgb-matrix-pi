"""
Bidirectional Search
Searches from both start and end simultaneously until they meet
Creates two expanding wavefronts that collide in the middle
"""

from collections import deque
from .base import PathfindingAlgorithm


class BidirectionalAlgorithm(PathfindingAlgorithm):
    def __init__(self):
        super().__init__("Bidirectional Search")
    
    def find_path(self, start, end, width, height, obstacles=None):
        """
        Bidirectional search - explores from both start and end
        Visual effect: Two wavefronts expanding toward each other
        """
        if obstacles is None:
            obstacles = set()
        if start == end:
            yield ('found', [start])
            return
        
        # Forward search from start
        queue_forward = deque([start])
        visited_forward = {start}
        parent_forward = {start: None}
        
        # Backward search from end
        queue_backward = deque([end])
        visited_backward = {end}
        parent_backward = {end: None}
        
        # Alternate between forward and backward search
        while queue_forward and queue_backward:
            # Forward step
            if queue_forward:
                current = queue_forward.popleft()
                yield ('exploring', current)
                
                # Check if we've connected the two searches
                if current in visited_backward:
                    # Reconstruct path
                    path = self._reconstruct_bidirectional_path(
                        current, parent_forward, parent_backward
                    )
                    yield ('found', path)
                    return
                
                yield ('visited', current)
                
                for neighbor in self.get_neighbors(*current, width, height, obstacles):
                    if neighbor not in visited_forward:
                        visited_forward.add(neighbor)
                        parent_forward[neighbor] = current
                        queue_forward.append(neighbor)
            
            # Backward step
            if queue_backward:
                current = queue_backward.popleft()
                yield ('exploring', current)
                
                # Check if we've connected the two searches
                if current in visited_forward:
                    # Reconstruct path
                    path = self._reconstruct_bidirectional_path(
                        current, parent_forward, parent_backward
                    )
                    yield ('found', path)
                    return
                
                yield ('visited', current)
                
                for neighbor in self.get_neighbors(*current, width, height, obstacles):
                    if neighbor not in visited_backward:
                        visited_backward.add(neighbor)
                        parent_backward[neighbor] = current
                        queue_backward.append(neighbor)
        
        yield ('no_path', None)
    
    def _reconstruct_bidirectional_path(self, meeting_point, parent_forward, parent_backward):
        """Reconstruct path from start to end through meeting point"""
        # Build path from start to meeting point
        path_forward = []
        node = meeting_point
        while node is not None:
            path_forward.append(node)
            node = parent_forward.get(node)
        path_forward.reverse()
        
        # Build path from meeting point to end
        path_backward = []
        node = parent_backward.get(meeting_point)
        while node is not None:
            path_backward.append(node)
            node = parent_backward.get(node)
        
        return path_forward + path_backward
