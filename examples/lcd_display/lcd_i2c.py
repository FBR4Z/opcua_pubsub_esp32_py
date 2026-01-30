"""
LCD I2C Driver for PCF8574 backpack
Compatible with HD44780-based 16x2 and 20x4 LCD displays

This library provides a simple interface for controlling LCD displays
connected via PCF8574 I2C expander, commonly used in Arduino and
ESP32/ESP8266 projects.

Author: OPC UA PubSub ESP32 Project
License: MIT
"""

import utime


class LCD_I2C:
    """
    LCD display driver using I2C interface (PCF8574)
    
    Supports standard HD44780 commands in 4-bit mode with I2C backpack.
    Common I2C addresses: 0x27, 0x3F, 0x20, 0x38
    """
    
    # LCD Commands
    LCD_CLEARDISPLAY = 0x01
    LCD_RETURNHOME = 0x02
    LCD_ENTRYMODESET = 0x04
    LCD_DISPLAYCONTROL = 0x08
    LCD_CURSORSHIFT = 0x10
    LCD_FUNCTIONSET = 0x20
    LCD_SETCGRAMADDR = 0x40
    LCD_SETDDRAMADDR = 0x80
    
    # Display control flags
    LCD_DISPLAYON = 0x04
    LCD_CURSOROFF = 0x00
    LCD_BLINKOFF = 0x00
    
    # Entry mode flags
    LCD_ENTRYLEFT = 0x02
    LCD_ENTRYSHIFTDECREMENT = 0x00
    
    # Row offsets for different display sizes
    ROW_OFFSETS = [0x00, 0x40, 0x14, 0x54]
    
    def __init__(self, i2c, addr=0x27, cols=16, rows=2):
        """
        Initialize LCD display
        
        Args:
            i2c: MicroPython I2C object
            addr: I2C address of PCF8574 (default 0x27)
            cols: Number of columns (default 16)
            rows: Number of rows (default 2)
        """
        self.i2c = i2c
        self.addr = addr
        self.cols = cols
        self.rows = rows
        self._backlight = True
        
        # Initialization sequence
        utime.sleep_ms(50)
        
        # Initialize in 4-bit mode
        self._write4bits(0x03 << 4)
        utime.sleep_ms(5)
        self._write4bits(0x03 << 4)
        utime.sleep_ms(1)
        self._write4bits(0x03 << 4)
        self._write4bits(0x02 << 4)
        
        # Configure display
        self.command(self.LCD_FUNCTIONSET | 0x08)  # 2 lines, 5x8 font
        self.command(self.LCD_DISPLAYCONTROL | self.LCD_DISPLAYON | 
                     self.LCD_CURSOROFF | self.LCD_BLINKOFF)
        self.clear()
        self.command(self.LCD_ENTRYMODESET | self.LCD_ENTRYLEFT | 
                     self.LCD_ENTRYSHIFTDECREMENT)
    
    def _write4bits(self, data):
        """Write 4 bits to LCD via I2C"""
        # Backlight control on bit 3
        if self._backlight:
            data |= 0x08
        
        # Enable pulse
        data |= 0x04  # Enable HIGH
        self.i2c.writeto(self.addr, bytes([data]))
        utime.sleep_us(1)
        data &= ~0x04  # Enable LOW
        self.i2c.writeto(self.addr, bytes([data]))
        utime.sleep_us(50)
    
    def _send(self, data, mode):
        """Send byte to LCD (command or data)"""
        high = mode | (data & 0xF0)
        low = mode | ((data << 4) & 0xF0)
        
        self._write4bits(high)
        self._write4bits(low)
    
    def command(self, cmd):
        """Send command to LCD"""
        self._send(cmd, 0)
    
    def write_char(self, char):
        """Write a single character"""
        if isinstance(char, str):
            char = ord(char)
        self._send(char, 1)
    
    def write(self, text):
        """Write text string"""
        for char in text:
            self.write_char(char)
    
    def clear(self):
        """Clear display and return cursor home"""
        self.command(self.LCD_CLEARDISPLAY)
        utime.sleep_ms(2)
    
    def home(self):
        """Return cursor to home position"""
        self.command(self.LCD_RETURNHOME)
        utime.sleep_ms(2)
    
    def set_cursor(self, col, row):
        """
        Set cursor position
        
        Args:
            col: Column (0-indexed)
            row: Row (0-indexed)
        """
        if row >= self.rows:
            row = self.rows - 1
        addr = col + self.ROW_OFFSETS[row]
        self.command(self.LCD_SETDDRAMADDR | addr)
    
    def print_line(self, line, text):
        """
        Write text to a specific line, padded/truncated to fit
        
        Args:
            line: Line number (0-indexed)
            text: Text to display
        """
        self.set_cursor(0, line)
        
        # Ensure text is string
        text = str(text)
        
        # Truncate if too long
        if len(text) > self.cols:
            text = text[:self.cols]
        
        # Write characters
        for char in text:
            self.write_char(char)
        
        # Pad with spaces
        for _ in range(self.cols - len(text)):
            self.write_char(' ')
    
    def print_center(self, line, text):
        """
        Write centered text to a specific line
        
        Args:
            line: Line number (0-indexed)
            text: Text to center
        """
        text = str(text)
        if len(text) > self.cols:
            text = text[:self.cols]
        
        spaces = (self.cols - len(text)) // 2
        centered_text = " " * spaces + text
        self.print_line(line, centered_text)
    
    def backlight(self, on=True):
        """
        Control backlight
        
        Args:
            on: True to turn on, False to turn off
        """
        self._backlight = on
        # Send dummy data to update backlight state
        self.i2c.writeto(self.addr, bytes([0x08 if on else 0x00]))
    
    def create_char(self, location, charmap):
        """
        Create custom character
        
        Args:
            location: Character slot (0-7)
            charmap: List of 8 bytes defining the character pattern
        """
        location &= 0x07
        self.command(self.LCD_SETCGRAMADDR | (location << 3))
        for byte in charmap:
            self._send(byte, 1)
        self.set_cursor(0, 0)  # Return to DDRAM


# Self-test when run directly
if __name__ == "__main__":
    import machine
    
    print("LCD I2C Test")
    print("=" * 40)
    
    # Initialize I2C
    i2c = machine.I2C(0, scl=machine.Pin(22), sda=machine.Pin(21), freq=400000)
    
    # Scan for devices
    devices = i2c.scan()
    print(f"I2C devices found: {[hex(d) for d in devices]}")
    
    if devices:
        # Try to initialize LCD
        addr = devices[0]
        print(f"Trying LCD at address 0x{addr:02x}")
        
        try:
            lcd = LCD_I2C(i2c, addr=addr)
            lcd.clear()
            lcd.print_line(0, "LCD I2C OK!")
            lcd.print_line(1, f"Addr: 0x{addr:02x}")
            print("SUCCESS: LCD initialized")
        except Exception as e:
            print(f"ERROR: {e}")
    else:
        print("No I2C devices found!")
        print("Check wiring: SDA->GPIO21, SCL->GPIO22")
