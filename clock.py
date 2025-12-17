from PIL import Image, ImageDraw, ImageFont
import time

class ClockDisplay:
    """Clock display class that renders time/date into an Image for the matrix."""
    def __init__(self, width, height, font=None):
        self.width = width
        self.height = height
        try:
            self.font = ImageFont.load_default() if font is None else font
        except Exception:
            self.font = None

    def render(self):
        now = time.localtime()
        timestr = time.strftime('%H:%M:%S', now)
        datestr = time.strftime('%Y-%m-%d', now)

        img = Image.new('RGB', (self.width, self.height), (0, 0, 0))
        draw = ImageDraw.Draw(img)
        # center time — use compatible sizing helper
        def _text_size(txt):
            try:
                return draw.textsize(txt, font=self.font)
            except Exception:
                try:
                    bbox = draw.textbbox((0, 0), txt, font=self.font)
                    return (bbox[2] - bbox[0], bbox[3] - bbox[1])
                except Exception:
                    try:
                        return self.font.getsize(txt)
                    except Exception:
                        return (len(txt) * 6, 8)

        if self.font:
            w, h = _text_size(timestr)
            draw.text(((self.width - w)//2, (self.height - h)//2 - 8), timestr, fill=(255,255,0), font=self.font)
            w2, h2 = _text_size(datestr)
            draw.text(((self.width - w2)//2, (self.height - h2)//2 + 12), datestr, fill=(0,255,255), font=self.font)
        else:
            draw.text((2, self.height//2-8), timestr, fill=(255,255,0))
            draw.text((2, self.height//2+8), datestr, fill=(0,255,255))

        return img
