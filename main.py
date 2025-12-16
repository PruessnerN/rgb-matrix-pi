#!/usr/bin/env python3
"""
RGB Matrix Pathfinding Visualizer - Main Orchestration
Runs multiple pathfinding algorithms in sequence
"""

from rgbmatrix import RGBMatrix, RGBMatrixOptions
from PIL import Image
import time
import random
import argparse

# Import pathfinding algorithms
from algorithms.bfs import BFSAlgorithm
from algorithms.dfs import DFSAlgorithm
from algorithms.dijkstra import DijkstraAlgorithm
from algorithms.astar import AStarAlgorithm


class PathfindingVisualizer:
    def __init__(self, rows=64, cols=64, hardware_mapping='adafruit-hat', gpio_slowdown=2):
        # Matrix configuration
        options = RGBMatrixOptions()
        options.rows = rows
        options.cols = cols
        options.chain_length = 1
        options.parallel = 1
        options.hardware_mapping = hardware_mapping
        options.gpio_slowdown = gpio_slowdown
        
        self.matrix = RGBMatrix(options=options)
        self.width = self.matrix.width
        self.height = self.matrix.height
        
        # Colors
        self.COLOR_BACKGROUND = (0, 0, 0)      # Black
        self.COLOR_START = (0, 255, 0)         # Green
        self.COLOR_END = (255, 0, 0)           # Red
        self.COLOR_EXPLORING = (0, 100, 255)   # Blue (currently exploring)
        self.COLOR_VISITED = (50, 50, 50)      # Dark gray (already visited)
        self.COLOR_PATH = (255, 255, 0)        # Yellow (final path)
        
        # Animation delay (seconds between steps)
        self.delay = 0.02
        
        # Initialize algorithms
        self.algorithms = [
            BFSAlgorithm(),
            DFSAlgorithm(),
            DijkstraAlgorithm(),
            AStarAlgorithm()
        ]
        
    def create_blank_canvas(self):
        """Create a blank image canvas"""
        return Image.new('RGB', (self.width, self.height), self.COLOR_BACKGROUND)
    
    def draw_pixel(self, image, x, y, color):
        """Draw a single pixel on the canvas"""
        if 0 <= x < self.width and 0 <= y < self.height:
            image.putpixel((x, y), color)
    
    def generate_random_points(self, min_distance=20):
        """Generate random start and end points with minimum distance"""
        while True:
            start = (random.randint(0, self.width - 1), random.randint(0, self.height - 1))
            end = (random.randint(0, self.width - 1), random.randint(0, self.height - 1))
            
            # Ensure minimum distance between start and end (Manhattan distance)
            distance = abs(start[0] - end[0]) + abs(start[1] - end[1])
            if distance > min_distance:
                return start, end
    
    def visualize_algorithm(self, algorithm, start, end):
        """Run and visualize a specific pathfinding algorithm"""
        print(f"\nRunning: {algorithm.name}")
        print(f"Start: {start}, End: {end}")
        
        # Create canvas
        image = self.create_blank_canvas()
        
        # Draw start and end points
        self.draw_pixel(image, start[0], start[1], self.COLOR_START)
        self.draw_pixel(image, end[0], end[1], self.COLOR_END)
        self.matrix.SetImage(image)
        time.sleep(1)  # Pause to show start/end
        
        # Run pathfinding algorithm
        for state_type, data in algorithm.find_path(start, end, self.width, self.height):
            if state_type == 'exploring':
                x, y = data
                # Don't overwrite start/end points
                if (x, y) != start and (x, y) != end:
                    self.draw_pixel(image, x, y, self.COLOR_EXPLORING)
                    self.matrix.SetImage(image)
                    time.sleep(self.delay)
            
            elif state_type == 'visited':
                x, y = data
                # Don't overwrite start/end points
                if (x, y) != start and (x, y) != end:
                    self.draw_pixel(image, x, y, self.COLOR_VISITED)
                    self.matrix.SetImage(image)
            
            elif state_type == 'found':
                path = data
                print(f"Path found! Length: {len(path)} steps")
                
                # Animate the final path
                time.sleep(0.5)
                for x, y in path:
                    if (x, y) != start and (x, y) != end:
                        self.draw_pixel(image, x, y, self.COLOR_PATH)
                        self.matrix.SetImage(image)
                        time.sleep(self.delay * 2)
                
                # Keep final result visible
                time.sleep(3)
                return True
            
            elif state_type == 'no_path':
                print("No path found!")
                time.sleep(2)
                return False
    
    def run(self, iterations=1):
        """Run pathfinding visualizations for all algorithms"""
        try:
            print("Starting Pathfinding Visualizer...")
            print(f"Algorithms: {', '.join(algo.name for algo in self.algorithms)}")
            print("Press CTRL-C to stop")
            
            for iteration in range(iterations):
                print(f"\n{'='*50}")
                print(f"Iteration {iteration + 1}/{iterations}")
                print('='*50)
                
                # Generate new random points for this iteration
                start, end = self.generate_random_points()
                
                # Run each algorithm with the same start/end points
                for algorithm in self.algorithms:
                    self.visualize_algorithm(algorithm, start, end)
                    time.sleep(1)  # Pause between algorithms
                
                time.sleep(2)  # Pause between iterations
            
            print("\nVisualization complete!")
            
        except KeyboardInterrupt:
            print("\nStopped by user")
        finally:
            self.matrix.Clear()


def main():
    parser = argparse.ArgumentParser(description='Pathfinding Algorithm Visualizer')
    parser.add_argument('--led-rows', type=int, default=64, help='Matrix rows')
    parser.add_argument('--led-cols', type=int, default=64, help='Matrix columns')
    parser.add_argument('--led-gpio-mapping', default='adafruit-hat', 
                       help='GPIO mapping (adafruit-hat, regular, etc.)')
    parser.add_argument('--led-slowdown-gpio', type=int, default=2,
                       help='GPIO slowdown (0=no slowdown, 1-4=increasing slowdown)')
    parser.add_argument('--iterations', type=int, default=1, 
                       help='Number of complete cycles through all algorithms')
    parser.add_argument('--delay', type=float, default=0.02,
                       help='Delay between steps (seconds)')
    
    args = parser.parse_args()
    
    visualizer = PathfindingVisualizer(
        rows=args.led_rows,
        cols=args.led_cols,
        hardware_mapping=args.led_gpio_mapping,
        gpio_slowdown=args.led_slowdown_gpio
    )
    
    visualizer.delay = args.delay
    visualizer.run(iterations=args.iterations)


if __name__ == "__main__":
    main()
