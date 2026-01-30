# boot.py - WiFi Connection with LCD Feedback
# OPC UA PubSub LCD Example
import gc
gc.collect()

import network
import utime
import machine

# Import configuration
try:
    from config import WIFI_SSID, WIFI_PASSWORD, I2C_SCL_PIN, I2C_SDA_PIN
except ImportError:
    print("ERROR: config.py not found!")
    print("Copy config_example.py to config.py and edit with your settings.")
    raise SystemExit

def setup_lcd():
    """Initialize LCD (if available)"""
    try:
        from lcd_i2c import LCD_I2C
        i2c = machine.I2C(0, scl=machine.Pin(I2C_SCL_PIN), 
                         sda=machine.Pin(I2C_SDA_PIN), freq=400000)
        
        # Try common I2C addresses
        for addr in [0x27, 0x3F, 0x20, 0x38]:
            try:
                lcd = LCD_I2C(i2c, addr=addr)
                lcd.clear()
                print(f"[LCD] Found at 0x{addr:02x}")
                return lcd
            except:
                continue
    except Exception as e:
        print(f"[LCD] Init error: {e}")
    return None

# Initialize LCD (if available)
lcd = setup_lcd()
if lcd:
    lcd.clear()
    lcd.print_line(0, "ESP32 OPC UA")
    lcd.print_line(1, "Initializing...")
    utime.sleep(1)

# Connect WiFi
wlan = network.WLAN(network.STA_IF)
wlan.active(True)
utime.sleep(1)

if not wlan.isconnected():
    if lcd:
        lcd.clear()
        lcd.print_line(0, "Connecting WiFi")
    
    print("WiFi...", end="")
    wlan.connect(WIFI_SSID, WIFI_PASSWORD)
    
    for i in range(20):
        if wlan.isconnected():
            break
        
        # Show progress on LCD
        if lcd:
            dots = "." * (i % 4)
            lcd.print_line(1, "Please wait" + dots)
        
        print(".", end="")
        utime.sleep(1)

if wlan.isconnected():
    ip = wlan.ifconfig()[0]
    print(f"\nIP: {ip}")
    
    if lcd:
        lcd.clear()
        lcd.print_line(0, "WiFi Connected")
        lcd.print_line(1, ip)
        utime.sleep(2)
        lcd.clear()
else:
    print("\nWiFi FAILED!")
    if lcd:
        lcd.clear()
        lcd.print_line(0, "WiFi FAILED")
        lcd.print_line(1, "Check settings")

gc.collect()
print(f"RAM: {gc.mem_free()//1024} KB free")
