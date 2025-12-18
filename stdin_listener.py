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
        '\x1b[A': 'up',
        '\x1b[B': 'down',
        '\x1b[C': 'right',
        '\x1b[D': 'left',
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
        
        buffer = []
        escape_sequence_start = None
        
        while self.running:
            try:
                # Check if data is available
                ready, _, _ = select.select([sys.stdin], [], [], 0.01)
                if not ready:
                    # If we have an incomplete escape sequence that's been waiting too long, clear it
                    if escape_sequence_start is not None:
                        elapsed = time.time() - escape_sequence_start
                        if elapsed > 0.1:  # 100ms timeout for incomplete sequences
                            log.warning('Timeout waiting for escape sequence completion, clearing buffer: %r', ''.join(buffer))
                            buffer.clear()
                            escape_sequence_start = None
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
                    buffer = [ch]
                    escape_sequence_start = time.time()
                    continue
                
                # Building escape sequence
                if escape_sequence_start is not None:
                    buffer.append(ch)
                    seq = ''.join(buffer)
                    
                    # Check if we have a complete arrow key sequence (ESC[A/B/C/D)
                    if len(buffer) == 3 and buffer[1] == '[' and buffer[2] in ['A', 'B', 'C', 'D']:
                        key = self.ESCAPE_MAP.get(seq)
                        if key:
                            log.info('Arrow key detected: %s', key)
                            self.key_states[key] = True
                            self.key_press_time[key] = time.time()
                            self.last_direction = key
                            self.event_queue.put((key, True, time.time()))
                        else:
                            log.warning('Unrecognized arrow sequence: %r', seq)
                        
                        buffer.clear()
                        escape_sequence_start = None
                    # If sequence is getting too long, it's probably invalid
                    elif len(buffer) > 5:
                        log.warning('Invalid escape sequence (too long): %r', seq)
                        buffer.clear()
                        escape_sequence_start = None
                    
            except Exception as e:
                log.exception('Stdin read error: %s', e)
                buffer.clear()
                escape_sequence_start = None
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
        """Get and consume the last direction pressed (for games like snake)"""
        direction = self.last_direction
        self.last_direction = None
        return direction
