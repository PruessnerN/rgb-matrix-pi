"""
Jump Point Search (JPS)
Optimized pathfinding that "jumps" over empty spaces
Creates a sparse exploration pattern with long straight lines
Much faster than A* on open grids
"""

import heapq
from .base import PathfindingAlgorithm


class JumpPointSearchAlgorithm(PathfindingAlgorithm):
    def __init__(self):
        super().__init__("Jump Point Search")
    
    def find_path(self, start, end, width, height, obstacles=None):
        """
        Jump Point Search - skips intermediate nodes
        Visual effect: Sparse exploration with long jumps
        """
        if obstacles is None:
            obstacles = set()
        pq = [(0, 0, start)]
        visited = set()
        parent = {start: None}
        g_score = {start: 0}
        
        while pq:
            _, current_g, current = heapq.heappop(pq)
            
            if current in visited:
                continue
            
            visited.add(current)
            yield ('exploring', current)
            
            if current == end:
                # Reconstruct path with all intermediate steps
                path = self._reconstruct_full_path(end, parent)
                yield ('found', path)
                return
            
            yield ('visited', current)
            
            # Find jump points (cardinal directions)
            for dx, dy in [(0, 1), (1, 0), (0, -1), (-1, 0)]:
                jump_point = self._jump(current, (dx, dy), end, width, height, visited, obstacles)
                if jump_point and jump_point not in visited:
                    # Calculate cost to jump point
                    jump_cost = self.manhattan_distance(current, jump_point)
                    tentative_g = current_g + jump_cost
                    
                    if jump_point not in g_score or tentative_g < g_score[jump_point]:
                        g_score[jump_point] = tentative_g
                        h_score = self.manhattan_distance(jump_point, end)
                        f_score = tentative_g + h_score
                        parent[jump_point] = current
                        heapq.heappush(pq, (f_score, tentative_g, jump_point))
        
        yield ('no_path', None)
    
    def _jump(self, current, direction, goal, width, height, visited, obstacles):
        """
        Jump in a direction until hitting an obstacle or finding a jump point
        Returns the jump point or None
        """
        dx, dy = direction
        x, y = current
        
        # Jump in the direction
        nx, ny = x + dx, y + dy
        
        # Check bounds and obstacles
        if not (0 <= nx < width and 0 <= ny < height) or (nx, ny) in obstacles:
            return None
        
        next_node = (nx, ny)
        
        # If we reached the goal, return it
        if next_node == goal:
            return next_node
        
        # For simplicity, make small jumps (you can increase jump distance for more dramatic effect)
        # Jump 3 steps at a time
        for _ in range(3):
            nx, ny = nx + dx, ny + dy
            if not (0 <= nx < width and 0 <= ny < height) or (nx, ny) in obstacles:
                return next_node
            next_node = (nx, ny)
            if next_node == goal:
                return next_node
        
        return next_node
    
    def _reconstruct_full_path(self, end, parent):
        """
        Reconstruct the complete path including all intermediate steps between jump points
        """
        # First get the jump points path
        jump_path = []
        node = end
        while node is not None:
            jump_path.append(node)
            node = parent[node]
        jump_path.reverse()
        
        # Now fill in all intermediate steps between jump points
        full_path = []
        for i in range(len(jump_path) - 1):
            current = jump_path[i]
            next_point = jump_path[i + 1]
            
            # Add current point
            full_path.append(current)
            
            # Fill in intermediate steps
            x, y = current
            nx, ny = next_point
            
            # Determine direction
            dx = 0 if nx == x else (1 if nx > x else -1)
            dy = 0 if ny == y else (1 if ny > y else -1)
            
            # Add all intermediate points
            while (x, y) != next_point:
                x += dx
                y += dy
                if (x, y) != next_point:
                    full_path.append((x, y))
        
        # Add the final point
        full_path.append(jump_path[-1])
        
        return full_path
