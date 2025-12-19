from PIL import Image
import random
import logging
import os

log = logging.getLogger('snake')

class SnakeGame:
    """Snake game logic and rendering on a logical grid.

    Usage:
      game = SnakeGame(matrix, grid_size=32)
      while running:
          game.step(input_listener)
          image = game.render()
          matrix.SetImage(image)
    """
    def __init__(self, matrix, grid_size=32):
        self.matrix = matrix
        self.grid = grid_size
        self.cell_w = max(1, matrix.width // self.grid)
        self.cell_h = max(1, matrix.height // self.grid)
        # High score persistence
        self.high_score_dir = os.path.join(os.path.expanduser('~'), 'game-data', 'rgb-matrix-pi')
        os.makedirs(self.high_score_dir, exist_ok=True)
        self.high_score_path = os.path.join(self.high_score_dir, 'highscore.txt')
        self.high_score = self._load_high_score(self.high_score_path)
        self.new_high = False
        self.reset()

    def reset(self):
        self.snake = [(self.grid//2, self.grid//2 + i) for i in range(3)]
        self.direction = (0, -1)
        self.place_food()
        self.alive = True
        self.score = 0
        self.new_high = False

    def place_food(self):
        while True:
            fx = random.randint(0, self.grid-1)
            fy = random.randint(0, self.grid-1)
            if (fx, fy) not in self.snake:
                self.food = (fx, fy)
                break

    def update_direction(self, input_listener):
        """Update direction based on queued input (captures quick taps)."""
        new_dir = input_listener.consume_direction()
        if new_dir:
            old_dir = self.direction
            if new_dir == 'up' and self.direction != (0,1):
                self.direction = (0, -1)
            elif new_dir == 'down' and self.direction != (0,-1):
                self.direction = (0, 1)
            elif new_dir == 'left' and self.direction != (1,0):
                self.direction = (-1, 0)
            elif new_dir == 'right' and self.direction != (-1,0):
                self.direction = (1, 0)
            if self.direction != old_dir:
                log.info('Direction change: %s -> %s', old_dir, self.direction)
    
    def move(self):
        """Move the snake one step (called on game tick)"""
        head = self.snake[0]
        new_head = ((head[0] + self.direction[0]) % self.grid, (head[1] + self.direction[1]) % self.grid)
        log.debug('Move from %s to %s dir=%s', head, new_head, self.direction)
        if new_head in self.snake:
            self.alive = False
            log.info('Collision detected, game over')
            # Update high score if needed
            try:
                if self.score > self.high_score:
                    self.high_score = self.score
                    self.new_high = True
                    self._save_high_score(self.high_score_path, self.high_score)
                    log.info('New high score: %d', self.high_score)
            except Exception as e:
                log.warning('Failed to save high score: %s', e)
            return
        self.snake.insert(0, new_head)
        if new_head == self.food:
            self.score += 1
            log.info('Food eaten, score=%d', self.score)
            self.place_food()
        else:
            self.snake.pop()

    def _load_high_score(self, path):
        try:
            with open(path, 'r') as f:
                val = int(f.read().strip() or '0')
                return max(0, val)
        except Exception:
            return 0

    def _save_high_score(self, path, value):
        tmp = path + '.tmp'
        with open(tmp, 'w') as f:
            f.write(str(int(value)))
        os.replace(tmp, path)
    
    def step(self, input_listener):
        """Legacy combined method for backward compatibility"""
        self.update_direction(input_listener)
        self.move()

    def render(self):
        img = Image.new('RGB', (self.matrix.width, self.matrix.height), (0,0,0))
        for x,y in self.snake:
            for dx in range(self.cell_w):
                for dy in range(self.cell_h):
                    px = x * self.cell_w + dx
                    py = y * self.cell_h + dy
                    if 0 <= px < self.matrix.width and 0 <= py < self.matrix.height:
                        img.putpixel((px, py), (0,255,0))
        # food
        fx, fy = self.food
        for dx in range(self.cell_w):
            for dy in range(self.cell_h):
                px = fx * self.cell_w + dx
                py = fy * self.cell_h + dy
                if 0 <= px < self.matrix.width and 0 <= py < self.matrix.height:
                    img.putpixel((px, py), (255,0,0))
        return img
