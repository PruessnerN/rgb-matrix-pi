import threading
import time
import queue
import logging

log = logging.getLogger('hid_listener')
logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(name)s %(levelname)s: %(message)s')

try:
    import hid
except Exception:
    hid = None

# HID usage codes for arrow keys (keyboard boot protocol)
USAGE_ARROW_MAP = {
    0x52: 'up',
    0x51: 'down',
    0x4F: 'right',
    0x50: 'left',
}


class HIDListener:
    """Simple HID listener reading boot-report keyboards via hidapi.

    Usage:
      l = HIDListener(vid=0x046d, pid=0xc52b)  # vendor/product
      l.start()
      ev = l.get_event(timeout=1.0)

    Notes:
    - Requires `pip install hidapi` (or system hidapi libs).
    - Device permissions must allow opening `/dev/hidraw*` or use udev rule to set GROUP/MODE.
    """

    def __init__(self, vid=None, pid=None, device_path=None, debug_raw=False):
        self.vid = vid
        self.pid = pid
        self.device_path = device_path
        self.debug_raw = debug_raw  # log every raw report if True
        self.dev = None
        self.thread = None
        self.running = False
        self.event_queue = queue.Queue()
        self.key_states = {'up': False, 'down': False, 'left': False, 'right': False}
        self.key_press_time = {k: 0.0 for k in self.key_states}

    def _open(self):
        if hid is None:
            raise RuntimeError('hidapi not available; pip install hidapi')

        # Try open by path if provided
        try:
            if self.device_path:
                # hid.Device() open_path may be available; try hid.open_path
                try:
                    h = hid.device()
                    h.open_path(self.device_path)
                    return h
                except Exception:
                    # fallback to enumerate/open by vid/pid
                    pass

            if self.vid and self.pid:
                h = hid.device()
                h.open(self.vid, self.pid)
                return h

            # enumerate and pick first keyboard-like device
            for d in hid.enumerate():
                # match usage_page/usage or interface if present
                # prefer devices with usage_page==1 (Generic Desktop) and usage==6 (Keyboard)
                # but not all enumerators expose that; fall back to first HID keyboard vendor device
                name = d.get('product_string') or d.get('manufacturer_string') or ''
                if 'keyboard' in name.lower() or 'logitech' in name.lower():
                    h = hid.device()
                    try:
                        h.open_path(d['path'])
                        return h
                    except Exception:
                        continue

            raise RuntimeError('No suitable HID device found')
        except Exception:
            raise

    def start(self):
        self.dev = self._open()
        # Log device info
        try:
            mfg = self.dev.get_manufacturer_string() or 'unknown'
            prod = self.dev.get_product_string() or 'unknown'
            serial = self.dev.get_serial_number_string() or 'unknown'
            log.info('HID device opened: %s %s (serial: %s)', mfg, prod, serial)
        except Exception as e:
            log.warning('Could not read device info: %s', e)
        
        # Set nonblocking mode to avoid read hangs
        try:
            self.dev.set_nonblocking(1)
            log.info('HID device set to nonblocking mode')
        except Exception as e:
            log.warning('Could not set nonblocking mode: %s', e)
        
        self.running = True
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()
        log.info('HID listener started')

    def stop(self):
        self.running = False
        try:
            if self.dev:
                try:
                    self.dev.close()
                except Exception:
                    pass
        except Exception:
            pass

    def _run(self):
        # hid.read returns list/bytes of report data
        prev_keys = set()
        error_count = 0
        max_errors = 10
        
        while self.running:
            try:
                data = None
                try:
                    # Nonblocking read with short timeout
                    data = self.dev.read(8, timeout_ms=100)
                except TypeError:
                    # some hid bindings use read(size) returning bytes without timeout
                    data = self.dev.read(8)
                except OSError as e:
                    # Specific OSError handling
                    log.error('HID read OSError: %s (errno: %s)', e, getattr(e, 'errno', 'none'))
                    error_count += 1
                    if error_count >= max_errors:
                        log.error('Too many read errors (%d), stopping HID listener', error_count)
                        self.running = False
                        break
                    time.sleep(0.1)
                    continue

                if not data:
                    time.sleep(0.01)  # small sleep if no data
                    continue
                
                # Reset error counter on successful read
                error_count = 0

                # Ensure we have a sequence of ints
                if isinstance(data, bytes):
                    buf = list(data)
                else:
                    buf = list(data)

                # Boot keyboard report: [mod, reserved, k1, k2, k3, k4, k5, k6]
                keys = set()
                for usage in buf[2:]:
                    if usage == 0:
                        continue
                    name = USAGE_ARROW_MAP.get(usage)
                    if name:
                        keys.add(name)

                # compute down/up
                down = keys - prev_keys
                up = prev_keys - keys
                
                # Only log if there are key events or debug_raw is on
                if self.debug_raw or down or up:
                    log.info('HID raw report: %s (keys: %s)', buf, keys or 'none')
                
                ts = time.time()
                for k in down:
                    self.key_states[k] = True
                    self.key_press_time[k] = ts
                    self.event_queue.put((k, True, ts))
                    log.info('HID event DOWN %s', k)
                for k in up:
                    self.key_states[k] = False
                    self.event_queue.put((k, False, ts))
                    log.info('HID event UP %s', k)

                prev_keys = keys
            except Exception as e:
                log.exception('HID read error: %s (type: %s)', e, type(e).__name__)
                error_count += 1
                if error_count >= max_errors:
                    log.error('Too many read errors (%d), stopping HID listener', error_count)
                    self.running = False
                    break
                time.sleep(0.5)

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
