#!/usr/bin/env python3
"""
RGB Matrix Pathfinding Visualizer - Main Orchestration
Runs multiple pathfinding algorithms in sequence
"""

from rgbmatrix import RGBMatrix, RGBMatrixOptions
from PIL import Image, ImageDraw, ImageFont
import time
import random
import argparse
import threading
import queue
import os
import logging

from stdin_listener import StdinListener as InputListener
from clock import ClockDisplay
from snake import SnakeGame

# Import pathfinding algorithms
from algorithms.bfs import BFSAlgorithm
from algorithms.dijkstra import DijkstraAlgorithm
from algorithms.astar import AStarAlgorithm
from algorithms.bidirectional import BidirectionalAlgorithm
from algorithms.greedy import GreedyBestFirstAlgorithm
from algorithms.jps import JumpPointSearchAlgorithm
from algorithms.random_walk import RandomWalkAlgorithm

# Import maze generators
from maze_generator import generate_random_walls, generate_maze_walls, generate_rooms

log = logging.getLogger('main')


class PathfindingVisualizer:
    def __init__(self, rows=64, cols=64, hardware_mapping='adafruit-hat', gpio_slowdown=2, 
                 pwm_bits=11, brightness=100, limit_refresh_rate=0, disable_hardware_pulsing=False):
        # Matrix configuration
        options = RGBMatrixOptions()
        options.rows = rows
        options.cols = cols
        options.chain_length = 1
        options.parallel = 1
        options.hardware_mapping = hardware_mapping
        options.gpio_slowdown = gpio_slowdown
        
        # Anti-flickering options
        options.pwm_bits = pwm_bits  # Valid range: 1-11 (lower = less flickering but fewer colors)
        options.brightness = brightness  # 1-100
        options.pwm_lsb_nanoseconds = 60  # Lower values = less ghosting/flickering
        options.limit_refresh_rate_hz = limit_refresh_rate  # 0 = no limit
        options.disable_hardware_pulsing = disable_hardware_pulsing  # Try True if flickering persists
        
        self.matrix = RGBMatrix(options=options)
        self.width = self.matrix.width
        self.height = self.matrix.height
        # (Using direct SetImage updates)
        
        # Colors
        self.COLOR_BACKGROUND = (0, 0, 0)      # Black
        self.COLOR_START = (0, 255, 0)         # Green
        self.COLOR_END = (255, 0, 0)           # Red
        self.COLOR_EXPLORING = (0, 100, 255)   # Blue (currently exploring)
        self.COLOR_VISITED = (20, 20, 20)      # Almost black (already visited)
        self.COLOR_PATH = (255, 255, 0)        # Yellow (final path)
        self.COLOR_WALL = (100, 0, 100)        # Deep purple (obstacles/walls)
        
        # Animation delay (seconds between steps)
        self.delay = 0.02
        
        # Initialize algorithms
        self.algorithms = [
            BFSAlgorithm(),
            DijkstraAlgorithm(),
            AStarAlgorithm(),
            BidirectionalAlgorithm(),
            GreedyBestFirstAlgorithm(),
            JumpPointSearchAlgorithm(),
            RandomWalkAlgorithm()
        ]
        
    def create_blank_canvas(self):
        """Create a blank image canvas"""
        return Image.new('RGB', (self.width, self.height), self.COLOR_BACKGROUND)
    
    def draw_pixel(self, image, x, y, color):
        """Draw a single pixel on the canvas"""
        if 0 <= x < self.width and 0 <= y < self.height:
            image.putpixel((x, y), color)

    # Using direct SetImage updates to the matrix (no throttling/frame-canvas)
    
    def generate_random_points(self, min_distance=20):
        """Generate random start and end points with minimum distance"""
        while True:
            start = (random.randint(0, self.width - 1), random.randint(0, self.height - 1))
            end = (random.randint(0, self.width - 1), random.randint(0, self.height - 1))
            
            # Ensure minimum distance between start and end (Manhattan distance)
            distance = abs(start[0] - end[0]) + abs(start[1] - end[1])
            if distance > min_distance:
                return start, end
    
    def visualize_algorithm(self, algorithm, start, end, obstacles=None, stop_event=None):
        """Run and visualize a specific pathfinding algorithm"""
        if obstacles is None:
            obstacles = set()
        
        print(f"\nRunning: {algorithm.name}")
        print(f"Start: {start}, End: {end}")
        
        # Create canvas
        image = self.create_blank_canvas()
        
        # Draw obstacles/walls
        for ox, oy in obstacles:
            self.draw_pixel(image, ox, oy, self.COLOR_WALL)
        
        # Draw start and end points
        self.draw_pixel(image, start[0], start[1], self.COLOR_START)
        self.draw_pixel(image, end[0], end[1], self.COLOR_END)
        # Show start/end immediately
        self.matrix.SetImage(image)
        time.sleep(1)  # Pause to show start/end
        
        # Run pathfinding algorithm
        for state_type, data in algorithm.find_path(start, end, self.width, self.height, obstacles):
            if stop_event is not None and stop_event.is_set():
                print(f"Stopping algorithm '{algorithm.name}' due to mode change")
                return False
            if state_type == 'exploring':
                x, y = data
                # Don't overwrite start/end points or walls
                if (x, y) != start and (x, y) != end and (x, y) not in obstacles:
                    self.draw_pixel(image, x, y, self.COLOR_EXPLORING)
                    self.matrix.SetImage(image)
                    time.sleep(self.delay)
            
            elif state_type == 'visited':
                x, y = data
                # Don't overwrite start/end points or walls
                if (x, y) != start and (x, y) != end and (x, y) not in obstacles:
                    self.draw_pixel(image, x, y, self.COLOR_VISITED)
                    self.matrix.SetImage(image)
            
            elif state_type == 'found':
                path = data
                print(f"Path found! Length: {len(path)} steps")
                print(f"Path: {path[:10]}..." if len(path) > 10 else f"Path: {path}")
                
                # Animate the final path
                time.sleep(0.5)
                for x, y in path:
                    if (x, y) != start and (x, y) != end and (x, y) not in obstacles:
                        self.draw_pixel(image, x, y, self.COLOR_PATH)
                        # Immediate update for final path animation
                        self.matrix.SetImage(image)
                        time.sleep(self.delay * 2)
                
                # Keep final result visible
                time.sleep(3)
                return True
            
            elif state_type == 'no_path':
                print("No path found!")
                time.sleep(2)
                return False
    
    def run(self, iterations=1, maze_type='none'):
        """Run pathfinding visualizations for all algorithms"""
        try:
            print("Starting Pathfinding Visualizer...")
            print(f"Algorithms: {', '.join(algo.name for algo in self.algorithms)}")
            print(f"Maze type: {maze_type}")
            print("Press CTRL-C to stop")
            
            for iteration in range(iterations):
                print(f"\n{'='*50}")
                print(f"Iteration {iteration + 1}/{iterations}")
                print('='*50)
                
                # Generate random points for this iteration
                start, end = self.generate_random_points()
                
                # Randomize algorithm order for each iteration
                shuffled_algorithms = self.algorithms.copy()
                random.shuffle(shuffled_algorithms)
                
                # Track which maze type to use for alternate mode
                maze_types = ['random', 'walls', 'rooms']
                maze_index = 0
                
                # Run each algorithm with the same start/end points but NEW obstacles each time
                for algorithm in shuffled_algorithms:
                    # Determine current maze type
                    if maze_type == 'alternate':
                        current_maze_type = maze_types[maze_index % len(maze_types)]
                        maze_index += 1
                    else:
                        current_maze_type = maze_type
                    
                    # Generate fresh obstacles for each algorithm
                    obstacles = set()
                    if current_maze_type == 'random':
                        obstacles = generate_random_walls(self.width, self.height, density=0.2)
                    elif current_maze_type == 'walls':
                        obstacles = generate_maze_walls(self.width, self.height, wall_length=10, num_walls=20)
                    elif current_maze_type == 'rooms':
                        obstacles = generate_rooms(self.width, self.height, num_rooms=6)
                    
                    # Keep areas around start/end clear
                    if current_maze_type != 'none':
                        for dx in range(-1, 2):
                            for dy in range(-1, 2):
                                obstacles.discard((start[0] + dx, start[1] + dy))
                                obstacles.discard((end[0] + dx, end[1] + dy))
                    
                    self.visualize_algorithm(algorithm, start, end, obstacles)
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
    parser.add_argument('--led-slowdown-gpio', type=int, default=5,
                       help='GPIO slowdown (0=no slowdown, 1-10=increasing slowdown)')
    parser.add_argument('--led-pwm-bits', type=int, default=5,
                       help='PWM bits (1-11, lower=less flickering but fewer colors)')
    parser.add_argument('--led-brightness', type=int, default=75,
                       help='Brightness level (1-100)')
    parser.add_argument('--led-limit-refresh', type=int, default=0,
                       help='Limit refresh rate in Hz (0=no limit, try 100-200 to reduce flicker)')
    parser.add_argument('--led-no-hardware-pulse', action='store_true',
                       help='Disable hardware pulsing (can reduce flicker)')
    parser.add_argument('--iterations', type=int, default=10, 
                       help='Number of complete cycles through all algorithms')
    parser.add_argument('--delay', type=float, default=0.02,
                       help='Delay between steps (seconds)')
    parser.add_argument('--maze', type=str, default='alternate',
                       choices=['none', 'random', 'walls', 'rooms', 'alternate'],
                       help='Maze/obstacle type: none (empty grid), random (scattered walls), walls (maze-like), rooms (rectangular rooms), alternate (cycles through all types)')
    parser.add_argument('--initial-mode', type=str, default='clock', choices=['clock', 'visualizer', 'snake'],
                       help='Initial mode to start in')
    parser.add_argument('--snake-grid', type=int, default=32,
                       help='Logical grid size for snake (default 32 => 2x2 pixels per cell on 64x64)')
    
    args = parser.parse_args()
    
    visualizer = PathfindingVisualizer(
        rows=args.led_rows,
        cols=args.led_cols,
        hardware_mapping=args.led_gpio_mapping,
        gpio_slowdown=args.led_slowdown_gpio,
        pwm_bits=args.led_pwm_bits,
        brightness=args.led_brightness,
        limit_refresh_rate=args.led_limit_refresh,
        disable_hardware_pulsing=args.led_no_hardware_pulse,
    )

    visualizer.delay = args.delay

    # Input listener (reads arrow keys from stdin)
    log.info('Starting stdin input listener (use arrow keys)')
    input_listener = InputListener()
    try:
        input_listener.start()
    except Exception as e:
        log.error('Input listener could not start: %s', e)

    current_mode = args.initial_mode
    mode_thread = None
    mode_stop = None

    def start_mode(mode_name):
        nonlocal mode_thread, mode_stop
        mode_stop = threading.Event()
        if mode_name == 'clock':
            # clock display uses ClockDisplay class
            clock_disp = ClockDisplay(visualizer.width, visualizer.height)
            def clock_runner():
                while not mode_stop.is_set():
                    visualizer.matrix.SetImage(clock_disp.render())
                    for _ in range(10):
                        if mode_stop.is_set():
                            break
                        time.sleep(0.1)

            mode_thread = threading.Thread(target=clock_runner, daemon=True)
        elif mode_name == 'snake':
            # snake game uses SnakeGame class
            def snake_runner():
                game = SnakeGame(visualizer.matrix, grid_size=args.snake_grid)
                tick = 0.16  # Game update speed (slightly slower for control)
                last_update = time.time()
                
                while not mode_stop.is_set():
                    if not game.alive:
                        img = Image.new('RGB', (visualizer.width, visualizer.height), (0,0,0))
                        draw = ImageDraw.Draw(img)
                        msg = f'Score:{game.score}'
                        draw.text((2, visualizer.height//2-4), msg, fill=(255,255,0))
                        visualizer.matrix.SetImage(img)
                        time.sleep(2)
                        game.reset()
                        last_update = time.time()
                        continue

                    # Always update direction from input (even between game ticks)
                    game.update_direction(input_listener)
                    
                    # Check if it's time to move the snake
                    now = time.time()
                    if now - last_update >= tick:
                        game.move()
                        visualizer.matrix.SetImage(game.render())
                        last_update = now
                    
                    # Small sleep to avoid busy waiting
                    time.sleep(0.01)

            mode_thread = threading.Thread(target=snake_runner, daemon=True)
        elif mode_name == 'visualizer':
            def vis_runner():
                # run visualizer until stop
                maze_types = ['random', 'walls', 'rooms']
                maze_index = 0
                while not mode_stop.is_set():
                    start_pt, end_pt = visualizer.generate_random_points()
                    # generate obstacles per current maze (use --maze arg)
                    current_maze_type = args.maze
                    if current_maze_type == 'alternate':
                        current_maze_type = maze_types[maze_index % len(maze_types)]
                        maze_index += 1
                    obstacles = set()
                    if current_maze_type == 'random':
                        obstacles = generate_random_walls(visualizer.width, visualizer.height, density=0.2)
                    elif current_maze_type == 'walls':
                        obstacles = generate_maze_walls(visualizer.width, visualizer.height, wall_length=10, num_walls=20)
                    elif current_maze_type == 'rooms':
                        obstacles = generate_rooms(visualizer.width, visualizer.height, num_rooms=6)
                    # ensure start/end clear
                    for dx in range(-1,2):
                        for dy in range(-1,2):
                            obstacles.discard((start_pt[0]+dx, start_pt[1]+dy))
                            obstacles.discard((end_pt[0]+dx, end_pt[1]+dy))

                    # run each algorithm (interruptible via stop_event)
                    shuffled = visualizer.algorithms.copy()
                    random.shuffle(shuffled)
                    for alg in shuffled:
                        if mode_stop.is_set():
                            return
                        visualizer.visualize_algorithm(alg, start_pt, end_pt, obstacles, stop_event=mode_stop)
                        time.sleep(1)
                    time.sleep(2)

            mode_thread = threading.Thread(target=vis_runner, daemon=True)
        mode_thread.start()

    # start initial mode
    start_mode(current_mode)

    try:
        log.info('Main loop running in %s mode', current_mode)
        
        # Just keep the mode running indefinitely
        while True:
            time.sleep(1)

    except KeyboardInterrupt:
        print('Exiting')
    finally:
        if mode_stop:
            mode_stop.set()
        if mode_thread:
            mode_thread.join(timeout=1.0)
        try:
            input_listener.stop()
        except Exception:
            pass
        visualizer.matrix.Clear()


if __name__ == "__main__":
    main()
