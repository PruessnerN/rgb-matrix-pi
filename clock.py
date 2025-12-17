from PIL import Image, ImageDraw, ImageFont
import time
import os

class ClockDisplay:
    """Clock display class that renders time/date into an Image for the matrix.

    Renders 12-hour time without seconds (e.g. "1:23 PM") and date as "DEC 14".
    Attempts to use a bold truetype font for better readability; falls back to default.
    """
    def __init__(self, width, height, font=None):
        self.width = width
        self.height = height
        # Prefer a bold truetype font if available for better readability.
        self.time_font = None
        self.date_font = None
        if font is not None:
            # user provided font (ImageFont instance)
            self.time_font = font
            self.date_font = font
        else:
            tried_paths = [
                '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',
                '/usr/share/fonts/truetype/freefont/FreeSansBold.ttf',
                '/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf',
            ]
            font_path = None
            for p in tried_paths:
                if os.path.exists(p):
                    font_path = p
                    break
            try:
                if font_path:
                    # time font large, date smaller
                    self.time_font = ImageFont.truetype(font_path, size=max(8, int(self.height * 0.45)))
                    self.date_font = ImageFont.truetype(font_path, size=max(8, int(self.height * 0.18)))
                else:
                    # fallback to default bitmap font
                    self.time_font = ImageFont.load_default()
                    self.date_font = self.time_font
            except Exception:
                self.time_font = ImageFont.load_default()
                self.date_font = self.time_font

    def render(self):
        now = time.localtime()
        # 12-hour format without seconds, remove leading zero (e.g., '1:23 PM')
        timestr = time.strftime('%I:%M %p', now).lstrip('0')
        # Show date as 'DEC 14' (month abbrev uppercase + day)
        month = time.strftime('%b', now).upper()
        day = str(int(time.strftime('%d', now)))
        datestr = f"{month} {day}"

        img = Image.new('RGB', (self.width, self.height), (0, 0, 0))
        draw = ImageDraw.Draw(img)
        # helper to compute text size with fallbacks
        def _text_size(txt, font_obj):
            try:
                return draw.textsize(txt, font=font_obj)
            except Exception:
                try:
                    bbox = draw.textbbox((0, 0), txt, font=font_obj)
                    return (bbox[2] - bbox[0], bbox[3] - bbox[1])
                except Exception:
                    try:
                        return font_obj.getsize(txt)
                    except Exception:
                        return (len(txt) * 6, 8)

        # time centered near top, date centered below
        tf = self.time_font
        df = self.date_font
        w, h = _text_size(timestr, tf)
        time_x = (self.width - w) // 2
        time_y = max(0, (self.height - h) // 2 - int(self.height * 0.12))
        draw.text((time_x, time_y), timestr, fill=(255, 255, 0), font=tf)

        w2, h2 = _text_size(datestr, df)
        date_x = (self.width - w2) // 2
        date_y = time_x + h + 4 if False else time_y + h + 4
        draw.text((date_x, date_y), datestr, fill=(0, 255, 255), font=df)

        return img
