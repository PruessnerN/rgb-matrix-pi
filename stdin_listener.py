import threading
import queue
import time
import sys
import termios
import tty
import select
import logging
import signal
import os

log = logging.getLogger('stdin_listener')


class StdinListener:
    """Listens to stdin for arrow key escape sequences.
    
    Reads raw stdin and maps escape sequences to arrow keys:
    - ESC[A = up
    - ESC[B = down
    - ESC[C = right
    - ESC[D = left
    
    Usage: run in headless/TTY mode where stdin is a terminal.
    """

    ESCAPE_MAP = {
        '\x1b[A': 'up',      # CSI arrow
        '\x1b[B': 'down',
        '\x1b[C': 'right',
        '\x1b[D': 'left',
        '\x1bOA': 'up',      # SS3 arrow (some keyboards/terminals)
        '\x1bOB': 'down',
        '\x1bOC': 'right',
        '\x1bOD': 'left',
    }

    def __init__(self):
        self.thread = None
        self.running = False
        self.event_queue = queue.Queue()
        self.key_states = {'up': False, 'down': False, 'left': False, 'right': False}
        self.key_press_time = {'up': 0.0, 'down': 0.0, 'left': 0.0, 'right': 0.0}
        self.last_direction = None  # Track last pressed direction for snake
        self.old_settings = None

    def start(self):
        if not sys.stdin.isatty():
            log.warning('stdin is not a TTY; stdin listener may not work properly')
        
        # Save terminal settings
        try:
            self.old_settings = termios.tcgetattr(sys.stdin)
        except Exception as e:
            log.warning('Could not get terminal settings: %s', e)
        
        self.running = True
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()
        log.info('Stdin listener started')

    def stop(self):
        self.running = False
        # Restore terminal settings immediately
        if self.old_settings:
            try:
                termios.tcsetattr(sys.stdin, termios.TCSANOW, self.old_settings)
                log.info('Terminal settings restored')
            except Exception as e:
                log.warning('Could not restore terminal: %s', e)

    def _run(self):
        # Set terminal to raw mode
        try:
            tty.setraw(sys.stdin.fileno())
            log.info('Terminal set to raw mode successfully')
        except Exception as e:
            log.error('Could not set raw mode: %s', e)
            return
        
        log.info('Stdin read loop starting, waiting for input...')
        
        while self.running:
            try:
                # Wait for input with short timeout for responsiveness
                ready, _, _ = select.select([sys.stdin], [], [], 0.01)
                if not ready:
                    continue
                
                # Read one character
                ch = sys.stdin.read(1)
                if not ch:
                    continue
                
                # Handle Ctrl+C immediately
                if ch == '\x03':
                    log.info('Ctrl+C detected, raising KeyboardInterrupt')
                    self.running = False
                    if self.old_settings:
                        try:
                            termios.tcsetattr(sys.stdin, termios.TCSANOW, self.old_settings)
                        except Exception:
                            pass
                    os.kill(os.getpid(), signal.SIGINT)
                    break
                
                # Start of escape sequence
                if ch == '\x1b':
                    # Read up to 3 more characters quickly (enough for CSI/SS3 arrows)
                    sequence = [ch]
                    for _ in range(3):
                        ready, _, _ = select.select([sys.stdin], [], [], 0.01)
                        if not ready:
                            break
                        nch = sys.stdin.read(1)
                        if not nch:
                            break
                        sequence.append(nch)

                    seq_str = ''.join(sequence)
                    key = self.ESCAPE_MAP.get(seq_str)
                    if key:
                        self.key_states[key] = True
                        self.key_press_time[key] = time.time()
                        self.last_direction = key
                        self.event_queue.put((key, True, time.time()))
                    # ignore unknown sequences silently
                    continue

            except Exception as e:
                log.exception('Stdin read error: %s', e)
                time.sleep(0.1)
        
        # Always restore terminal when exiting
        if self.old_settings:
            try:
                termios.tcsetattr(sys.stdin, termios.TCSANOW, self.old_settings)
                log.info('Terminal restored at exit')
            except Exception:
                pass

    def get_event(self, timeout=None):
        try:
            return self.event_queue.get(timeout=timeout)
        except queue.Empty:
            return None

    def is_pressed(self, key):
        return self.key_states.get(key, False)

    def pressed_duration(self, key):
        if not self.is_pressed(key):
            return 0.0
        return time.time() - self.key_press_time.get(key, 0.0)
    
    def get_last_direction(self):
        """Get the last direction pressed (doesn't clear it - persists until new direction)"""
        return self.last_direction
    
    def consume_last_direction(self):
        """Get and clear the last direction"""
        direction = self.last_direction
        self.last_direction = None
        return direction
