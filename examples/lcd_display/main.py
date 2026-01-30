"""
OPC UA PubSub LCD Example - Main Application
Demonstrates OPC UA PubSub JSON encoding with LCD feedback on ESP32

This example cycles through different OPC UA data types and displays
the current type and value on an I2C LCD display while publishing
to an MQTT broker using OPC UA PubSub JSON format.
"""
import utime
import urandom
import network
import machine
import gc
from lcd_i2c import LCD_I2C
from opcua_micro import DataValue, NetworkMessage, ESPTransport

# Import configuration
try:
    from config import (MQTT_BROKER, MQTT_PORT, PUBLISHER_ID,
                       I2C_SCL_PIN, I2C_SDA_PIN, PUBLISH_INTERVAL, DEBUG)
except ImportError:
    print("ERROR: config.py not found!")
    print("Copy config_example.py to config.py and edit with your settings.")
    raise SystemExit


class DataGenerator:
    """Generates random data of different OPC UA types"""
    
    DATA_TYPES = [
        ("BOOL", "Boolean"),
        ("INT16", "Int16"),
        ("UINT16", "UInt16"),
        ("INT32", "Int32"),
        ("FLOAT", "Float"),
        ("DOUBLE", "Double"),
        ("STR", "String"),
        ("DT", "DateTime")
    ]
    
    def __init__(self):
        self.type_index = 0
        self.value = 0
        self.str_values = ["OPCUA", "ESP32", "TEST", "LCD", "MQTT", "JSON"]
        self.str_index = 0
    
    def next_data(self):
        """Generate next data set"""
        type_short, type_full = self.DATA_TYPES[self.type_index]
        
        # Generate value based on type
        if type_full == "Boolean":
            self.value = urandom.getrandbits(1) == 1
        elif type_full == "Int16":
            self.value = urandom.randint(-32768, 32767)
        elif type_full == "UInt16":
            self.value = urandom.randint(0, 65535)
        elif type_full == "Int32":
            self.value = urandom.randint(-100000, 100000)
        elif type_full in ["Float", "Double"]:
            self.value = round(urandom.uniform(-100, 100), 2)
        elif type_full == "String":
            self.value = self.str_values[self.str_index]
            self.str_index = (self.str_index + 1) % len(self.str_values)
        elif type_full == "DateTime":
            self.value = f"2024-01-{urandom.randint(10,31):02d}T" \
                       f"{urandom.randint(10,23):02d}:{urandom.randint(10,59):02d}:00Z"
        
        self.type_index = (self.type_index + 1) % len(self.DATA_TYPES)
        return type_short, type_full, self.value
    
    def get_display_text(self, type_short, value):
        """Format text for LCD display"""
        line1 = f"TYPE: {type_short}"
        
        if isinstance(value, bool):
            val_str = "TRUE" if value else "FALSE"
        elif isinstance(value, str):
            val_str = value[:13] + "..." if len(value) > 13 else value
        elif isinstance(value, float):
            val_str = f"{value:.2f}"
        else:
            val_str = str(value)
        
        val_str = val_str[:16]
        padding = (16 - len(val_str)) // 2
        line2 = " " * padding + val_str
        
        return line1, line2[:16]


def setup_lcd():
    """Initialize LCD I2C display"""
    try:
        i2c = machine.I2C(0, scl=machine.Pin(I2C_SCL_PIN), 
                         sda=machine.Pin(I2C_SDA_PIN), freq=400000)
        
        devices = i2c.scan()
        if DEBUG:
            print(f"[I2C] Devices: {[hex(d) for d in devices]}")
        
        if not devices:
            print("[I2C] No devices found!")
            return None
        
        # Try common addresses
        for addr in [0x27, 0x3F, 0x20, 0x38]:
            if addr in devices:
                print(f"[LCD] Found at 0x{addr:02x}")
                lcd = LCD_I2C(i2c, addr=addr)
                lcd.clear()
                return lcd
        
        return None
        
    except Exception as e:
        print(f"[LCD] Error: {e}")
        return None


def wait_for_wifi(lcd=None, timeout=30):
    """Wait for WiFi connection, show status on LCD"""
    wlan = network.WLAN(network.STA_IF)
    start_time = utime.time()
    
    if lcd:
        lcd.clear()
        lcd.print_line(0, "Connecting WiFi")
    
    print("[WiFi] Waiting for connection...")
    
    while not wlan.isconnected():
        if utime.time() - start_time > timeout:
            print("[WiFi] Timeout!")
            if lcd:
                lcd.clear()
                lcd.print_line(0, "WiFi FAILED")
                lcd.print_line(1, "Check settings")
            return False
        
        if lcd:
            dots = "." * ((utime.time() - start_time) % 4)
            lcd.print_line(1, "Please wait" + dots)
        
        utime.sleep(0.5)
    
    ip = wlan.ifconfig()[0]
    print(f"[WiFi] Connected! IP: {ip}")
    
    if lcd:
        lcd.clear()
        lcd.print_line(0, "WiFi OK!")
        lcd.print_line(1, ip)
        utime.sleep(2)
    
    return True


def setup_opcua(lcd):
    """Configure OPC UA PubSub system"""
    if lcd:
        lcd.clear()
        lcd.print_line(0, "Connecting MQTT")
        lcd.print_line(1, "Please wait...")
    
    transport = ESPTransport(PUBLISHER_ID, MQTT_BROKER, port=MQTT_PORT)
    publisher = NetworkMessage(f"urn:esp32:lcd:{PUBLISHER_ID}")
    
    if not transport.connect():
        print("[MQTT] Connection failed!")
        if lcd:
            lcd.clear()
            lcd.print_line(0, "MQTT ERROR")
            lcd.print_line(1, "Check broker IP")
        return None, None
    
    print("[MQTT] Connected!")
    
    if lcd:
        lcd.clear()
        lcd.print_line(0, "MQTT: OK")
        lcd.print_line(1, "OPC UA Active")
        utime.sleep(1)
    
    # Publish metadata
    meta_fields = {
        "DataType": "String",
        "Value": "Variant",
        "DisplayLine1": "String",
        "DisplayLine2": "String"
    }
    
    meta_json = publisher.create_metadata_json(1, meta_fields)
    transport.publish("opcua/lcd/metadata", meta_json, qos=1, retain=True)
    
    return transport, publisher


def main():
    """Main application loop"""
    print("\n=== OPC UA PubSub + LCD I2C Example ===\n")
    gc.collect()
    print(f"[RAM] Free: {gc.mem_free()//1024} KB")
    
    # 1. Initialize LCD first
    lcd = setup_lcd()
    
    if lcd:
        lcd.clear()
        lcd.print_line(0, "Starting...")
        lcd.print_line(1, "OPC UA System")
        utime.sleep(2)
    
    # 2. Wait for WiFi (may already be connected from boot.py)
    if not wait_for_wifi(lcd):
        return
    
    # 3. Configure OPC UA
    transport, publisher = setup_opcua(lcd)
    if not transport:
        return
    
    # 4. Initialize data generator
    generator = DataGenerator()
    sequence = 1
    
    print("\n[SYSTEM] Starting data transmission...")
    print("Press CTRL+C to stop\n")
    
    try:
        while True:
            # Generate new data
            type_short, type_full, value = generator.next_data()
            
            # Display on LCD
            if lcd:
                line1, line2 = generator.get_display_text(type_short, value)
                lcd.clear()
                lcd.print_line(0, line1)
                lcd.print_line(1, line2)
            else:
                line1 = f"TYPE: {type_short}"
                line2 = str(value)[:16]
            
            # Prepare OPC UA payload
            payload = {
                "DataType": DataValue(type_full, data_type='String'),
                "Value": DataValue(value, data_type=type_full),
                "DisplayLine1": DataValue(line1, data_type='String'),
                "DisplayLine2": DataValue(line2, data_type='String')
            }
            
            # Send JSON message
            json_msg = publisher.create_json(1, sequence, payload)
            
            if transport.publish("opcua/lcd/data", json_msg, qos=1):
                print(f"[{sequence:04d}] {type_short}: {value}")
                # Visual feedback on LCD
                if lcd:
                    lcd.set_cursor(15, 0)
                    lcd.write_char('*')
            else:
                print(f"[{sequence:04d}] X Failed")
                if lcd:
                    lcd.set_cursor(15, 0)
                    lcd.write_char('!')
            
            sequence = (sequence % 9999) + 1
            
            # Wait with visual feedback
            for i in range(PUBLISH_INTERVAL * 2):
                utime.sleep_ms(500)
                if lcd and i % 2 == 0:
                    lcd.set_cursor(14, 1)
                    lcd.write_char('.')
    
    except KeyboardInterrupt:
        print("\n\n[SYSTEM] Interrupted by user")
    finally:
        if lcd:
            lcd.clear()
            lcd.print_line(0, "System")
            lcd.print_line(1, "Stopped")
        if transport:
            transport.disconnect()
        print("[SYSTEM] Finished")


if __name__ == "__main__":
    main()
