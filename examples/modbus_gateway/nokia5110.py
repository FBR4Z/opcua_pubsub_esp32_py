"""
Driver do display Nokia 5110 (PCD8544, 84x48) para a placa IT caseira v2.

Pinos (J14 da placa): DIN=13, CLK=14, CE=27, DC=26, RST=25.
Usa a SPI de hardware (HSPI) e um framebuf MONO_VLSB, que tem exatamente o
mesmo layout de memoria do PCD8544: todos os metodos do framebuf (text, line,
rect, fill_rect, pixel...) desenham no buffer e show() envia tudo ao display.
"""

import time
import framebuf
from machine import Pin, SPI


class Nokia5110(framebuf.FrameBuffer):
    W = 84
    H = 48

    def __init__(self, din=13, clk=14, ce=27, dc=26, rst=25, contrast=0xB8):
        self.buf = bytearray(self.W * self.H // 8)
        super().__init__(self.buf, self.W, self.H, framebuf.MONO_VLSB)
        self.ce = Pin(ce, Pin.OUT, value=1)
        self.dc = Pin(dc, Pin.OUT, value=0)
        self.rst = Pin(rst, Pin.OUT, value=1)
        self.spi = SPI(1, baudrate=2000000, polarity=0, phase=0,
                       sck=Pin(clk), mosi=Pin(din), miso=None)
        self.reset()
        self.init(contrast)

    def _write(self, data, dc):
        self.dc.value(dc)
        self.ce.value(0)
        self.spi.write(data)
        self.ce.value(1)

    def reset(self):
        self.rst.value(0)
        time.sleep_ms(50)
        self.rst.value(1)
        time.sleep_ms(50)

    def init(self, contrast=0xB8):
        # extended: Vop, temp coef, bias 1:48; basic: modo normal
        self._write(bytes([0x21, contrast, 0x04, 0x14, 0x20, 0x0C]), 0)

    def contrast(self, vop):
        """vop: 0x80..0xFF (tipico 0xB0..0xC0)."""
        self._write(bytes([0x21, vop & 0xFF, 0x20]), 0)

    def show(self):
        self._write(bytes([0x80, 0x40]), 0)
        self._write(self.buf, 1)
