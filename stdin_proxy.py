#!/usr/bin/env python3
"""Terminal stdin -> socket proxy.

Run this over SSH or in a terminal to forward arrow keys to the UNIX socket server.
It reads raw stdin bytes, maps arrow escape sequences to 'up/down/left/right', and sends
JSON events to the socket path.

Usage:
  python3 stdin_proxy.py --socket /tmp/rgb_input.sock

Press Ctrl-C to exit.
"""
import argparse
import socket
import json
import time
import sys
import termios
import tty
import logging

log = logging.getLogger('stdin_proxy')
logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(name)s %(levelname)s: %(message)s')


ESC_SEQ_MAP = {
    b'\x1b[A': 'up',
    b'\x1b[B': 'down',
    b'\x1b[C': 'right',
    b'\x1b[D': 'left',
}


class StdinProxy:
    def __init__(self, socket_path='/tmp/rgb_input.sock'):
        self.socket_path = socket_path
        self.sock = None

    def connect(self):
        try:
            s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            s.connect(self.socket_path)
            self.sock = s
            log.info('Connected to %s', self.socket_path)
            return True
        except Exception as e:
            log.info('Connect failed: %s', e)
            self.sock = None
            return False

    def send(self, key, is_down):
        if not self.sock:
            if not self.connect():
                return
        msg = json.dumps({'key': key, 'is_down': bool(is_down), 'ts': time.time()}) + '\n'
        try:
            self.sock.sendall(msg.encode('utf-8'))
            log.debug('Sent %s %s', key, 'DOWN' if is_down else 'UP')
        except Exception as e:
            log.info('Send failed: %s', e)
            try:
                self.sock.close()
            except Exception:
                pass
            self.sock = None

    def run(self):
        fd = sys.stdin.fileno()
        old = termios.tcgetattr(fd)
        try:
            tty.setraw(fd)
            buf = b''
            log.info('Reading stdin in raw mode. Press arrows to send events, Ctrl-C to quit.')
            while True:
                b = sys.stdin.buffer.read(1)
                if not b:
                    break
                buf += b
                # if buffer matches any escape seq
                for seq, name in ESC_SEQ_MAP.items():
                    if buf.endswith(seq):
                        # send down then up (terminal only gives sequence once)
                        self.send(name, True)
                        self.send(name, False)
                        buf = b''
                        break
                # also allow plain letters (e.g., 'q' to quit)
                if b == b'q':
                    log.info('q pressed; exiting')
                    return
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--socket', default='/tmp/rgb_input.sock')
    args = parser.parse_args()
    p = StdinProxy(socket_path=args.socket)
    p.run()


if __name__ == '__main__':
    main()
