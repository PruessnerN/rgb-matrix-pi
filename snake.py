from PIL import Image
import random
import logging
import os

log = logging.getLogger('snake')

def _get_user_home():
    """Get the actual user's home directory, accounting for sudo."""
    if os.environ.get('SUDO_USER'):
        import pwd
        return pwd.getpwnam(os.environ['SUDO_USER']).pw_dir
    return os.path.expanduser('~')

def _ensure_game_data_dir():
    """Ensure game-data directory exists and is writable at a single path."""
    target = os.path.join('/var', 'tmp', 'rgb-matrix-pi')  # persistent on most systems

    try:
        os.makedirs(target, exist_ok=True, mode=0o777)
        if os.environ.get('SUDO_USER'):
            try:
                import pwd
                user_info = pwd.getpwnam(os.environ['SUDO_USER'])
                os.chown(target, user_info.pw_uid, user_info.pw_gid)
            except Exception as chown_err:
                # Chown is best-effort; don't warn if it fails on system-managed dirs like /var/tmp
                log.debug('Chown skipped/failed for %s: %s', target, chown_err)
        return target
    except PermissionError as e:
        log.error('Permission denied creating %s: %s', target, e)
    except Exception as e:
        log.error('Failed to create %s: %s', target, e)

    log.error('Could not ensure a writable game-data directory; high scores will be disabled.')
    return None

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
        try:
            self.high_score_dir = _ensure_game_data_dir()
            self.high_score_path = os.path.join(self.high_score_dir, 'highscore.txt') if self.high_score_dir else None
        except Exception as e:
            log.error('Could not set up high score directory: %s. High scores will not persist.', e)
            self.high_score_dir = None
            self.high_score_path = None
        self.high_score = self._load_high_score(self.high_score_path) if self.high_score_path else 0
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
                log.debug('Direction change: %s -> %s', old_dir, self.direction)
    
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
        if not path:
            return  # High score persistence disabled
        tmp = path + '.tmp'
        try:
            with open(tmp, 'w') as f:
                f.write(str(int(value)))
            os.replace(tmp, path)
        except PermissionError as e:
            log.error('Permission denied saving high score to %s: %s', path, e)
        except Exception as e:
            log.error('Failed to save high score: %s', e)
    
    def step(self, input_listener):
        """Legacy combined method for backward compatibility"""
        self.update_direction(input_listener)
        self.move()

    def render(self):
        img = Image.new('RGB', (self.matrix.width, self.matrix.height), (0,0,0))
        for idx, (x, y) in enumerate(self.snake):
            color = (0, 120, 0) if idx == 0 else (0, 255, 0)
            for dx in range(self.cell_w):
                for dy in range(self.cell_h):
                    px = x * self.cell_w + dx
                    py = y * self.cell_h + dy
                    if 0 <= px < self.matrix.width and 0 <= py < self.matrix.height:
                        img.putpixel((px, py), color)
        # food
        fx, fy = self.food
        for dx in range(self.cell_w):
            for dy in range(self.cell_h):
                px = fx * self.cell_w + dx
                py = fy * self.cell_h + dy
                if 0 <= px < self.matrix.width and 0 <= py < self.matrix.height:
                    img.putpixel((px, py), (255,0,0))
        return img
