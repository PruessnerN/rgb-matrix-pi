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
        
        buf = ''
        char_count = 0
        while self.running:
            try:
                # Non-blocking read with timeout
                ready, _, _ = select.select([sys.stdin], [], [], 0.1)
                if not ready:
                    continue
                
                ch = sys.stdin.read(1)
                if not ch:
                    time.sleep(0.01)
                    continue
                
                char_count += 1
                log.debug('Read char #%d: %r (hex: %s)', char_count, ch, ch.encode('latin-1').hex())
                
                # Build escape sequence buffer
                if ch == '\x1b':
                    buf = ch
                    # Read next chars quickly (for escape sequences like ESC[A)
                    # Arrow keys send 3 chars: ESC [ letter, need to wait for all
                    time.sleep(0.005)  # Small delay for sequence to arrive
                    attempts = 0
                    max_attempts = 20
                    while attempts < max_attempts and len(buf) < 3:
                        ready, _, _ = select.select([sys.stdin], [], [], 0.02)
                        if ready:
                            nch = sys.stdin.read(1)
                            if nch:
                                buf += nch
                                log.debug('  Escape sequence building: %r', buf)
                        attempts += 1
                        if len(buf) >= 3:
                            break
                    
                    log.debug('Complete escape sequence: %r', buf)
                    
                    # Try to map escape sequence
                    key = self.ESCAPE_MAP.get(buf)
                    if key:
                        # Simulate key down
                        log.info('*** Stdin event: %s DOWN ***', key)
                        self.key_states[key] = True
                        self.key_press_time[key] = time.time()
                        self.event_queue.put((key, True, time.time()))
                        
                        # Auto-release after short delay (stdin doesn't have key-up events)
                        time.sleep(0.1)
                        log.info('*** Stdin event: %s UP ***', key)
                        self.key_states[key] = False
                        self.event_queue.put((key, False, time.time()))
                    else:
                        log.warning('Unrecognized escape sequence: %r', buf)
                    
                    buf = ''
                elif ch == '\x03':  # Ctrl+C
                    log.info('Ctrl+C detected, raising KeyboardInterrupt')
                    self.running = False
                    # Restore terminal before raising
                    if self.old_settings:
                        try:
                            termios.tcsetattr(sys.stdin, termios.TCSANOW, self.old_settings)
                        except Exception:
                            pass
                    # Send SIGINT to main process
                    os.kill(os.getpid(), signal.SIGINT)
                    break
                else:
                    # Log any other character for debugging
                    log.debug('Ignoring non-escape char: %r (hex: %s)', ch, ch.encode('latin-1').hex())
                
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
