#!/usr/bin/env python3
"""User-mode input proxy: captures keyboard with pynput and forwards events to UNIX socket.

Run this as your regular user in the desktop session:
  python3 input_proxy.py --socket /tmp/rgb_input.sock

It will retry connecting until the server socket appears.
"""
import argparse
import json
import socket
import time
import threading
import logging

log = logging.getLogger('input_proxy')
logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(name)s %(levelname)s: %(message)s')

try:
    from pynput import keyboard
    from pynput.keyboard import Key
except Exception:
    keyboard = None
    Key = None


class Proxy:
    def __init__(self, socket_path='/tmp/rgb_input.sock'):
        self.socket_path = socket_path
        self.sock = None
        self.lock = threading.Lock()

    def connect(self):
        while True:
            try:
                s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
                s.connect(self.socket_path)
                with self.lock:
                    self.sock = s
                log.info('Connected to %s', self.socket_path)
                return
            except Exception:
                log.info('Connect failed (socket missing?), retrying in 1s...')
                time.sleep(1.0)

    def send(self, key, is_down, ts=None):
        if ts is None:
            ts = time.time()
        msg = json.dumps({'key': key, 'is_down': bool(is_down), 'ts': ts}) + '\n'
        data = msg.encode('utf-8')
        try:
            with self.lock:
                if self.sock:
                    self.sock.sendall(data)
                    log.debug('Sent: %s %s', key, 'DOWN' if is_down else 'UP')
        except Exception as exc:
            log.warning('Send failed (%s), reconnecting', exc)
            # on failure, drop and reconnect
            try:
                with self.lock:
                    if self.sock:
                        self.sock.close()
                    self.sock = None
            except Exception:
                pass
            self.connect()

    def _map_key(self, key):
        try:
            if key == Key.up:
                return 'up'
            if key == Key.down:
                return 'down'
            if key == Key.left:
                return 'left'
            if key == Key.right:
                return 'right'
        except Exception:
            pass
        try:
            name = getattr(key, 'name', None)
            if name in ('up', 'down', 'left', 'right'):
                return name
        except Exception:
            pass
        return None

    def run(self):
        if keyboard is None:
            raise RuntimeError('pynput not available; install pynput')

        self.connect()

        def on_press(key):
            k = self._map_key(key)
            if k:
                self.send(k, True)

        def on_release(key):
            k = self._map_key(key)
            if k:
                self.send(k, False)

        listener = keyboard.Listener(on_press=on_press, on_release=on_release)
        listener.start()

        try:
            while True:
                time.sleep(1.0)
        except KeyboardInterrupt:
            try:
                with self.lock:
                    if self.sock:
                        self.sock.close()
            except Exception:
                pass


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--socket', default='/tmp/rgb_input.sock')
    args = parser.parse_args()
    p = Proxy(socket_path=args.socket)
    p.run()


if __name__ == '__main__':
    main()
