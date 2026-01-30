# OPC UA PubSub LCD Example for ESP32

A practical example demonstrating OPC UA PubSub JSON encoding with real-time LCD display feedback on ESP32 microcontrollers using MicroPython.

![MicroPython](https://img.shields.io/badge/MicroPython-1.20+-green)
![ESP32](https://img.shields.io/badge/Platform-ESP32-blue)
![License](https://img.shields.io/badge/License-MIT-yellow)

## Overview

This example showcases how to integrate OPC UA PubSub protocol with a 16x2 I2C LCD display, providing visual feedback of transmitted data types and values. It demonstrates the practical application of industrial IoT protocols on resource-constrained devices.

### Features

- **OPC UA PubSub JSON Encoding** - Compliant with IEC 62541-14
- **Multiple Data Types** - Boolean, Int16, UInt16, Float, String, DateTime
- **Real-time LCD Display** - Visual feedback of transmitted values
- **MQTT Transport** - Standard broker connectivity
- **Automatic WiFi Reconnection** - Robust network handling
- **Low Memory Footprint** - Optimized for ESP32 constraints

## Hardware Requirements

| Component | Specification |
|-----------|--------------|
| Microcontroller | ESP32 (any variant) |
| Display | LCD 16x2 with I2C backpack (PCF8574) |
| Connections | I2C: SDA→GPIO21, SCL→GPIO22 |

### Wiring Diagram

```
ESP32          LCD I2C Module
─────          ──────────────
3.3V    ────►  VCC
GND     ────►  GND
GPIO21  ────►  SDA
GPIO22  ────►  SCL
```

## Software Requirements

- MicroPython 1.20 or later
- MQTT Broker (Mosquitto, HiveMQ, etc.)
- [Thonny IDE](https://thonny.org/) or [mpremote](https://docs.micropython.org/en/latest/reference/mpremote.html)

## Installation

### 1. Clone this repository

```bash
git clone https://github.com/YOUR_USERNAME/opcua_pubsub_esp32.git
cd opcua_pubsub_esp32/examples/lcd_display
```

### 2. Configure your credentials

Copy the example configuration and edit with your settings:

```bash
cp config_example.py config.py
```

Edit `config.py` with your WiFi and MQTT broker settings:

```python
WIFI_SSID = "your_wifi_ssid"
WIFI_PASSWORD = "your_wifi_password"
MQTT_BROKER = "192.168.1.100"  # Your broker IP
```

### 3. Upload to ESP32

Using Thonny:
1. Open Thonny and connect to your ESP32
2. Upload all `.py` files to the device root
3. Reset the ESP32

Using mpremote:
```bash
mpremote connect /dev/ttyUSB0 cp *.py :
mpremote connect /dev/ttyUSB0 reset
```

## Usage

After uploading and resetting, the ESP32 will:

1. **Boot Phase** - Connect to WiFi and display IP address
2. **MQTT Connection** - Connect to the configured broker
3. **Data Transmission** - Cycle through different data types every 3 seconds

### LCD Display Output

```
┌────────────────┐
│BOOLEAN #1      │  ← Data type and sequence
│= TRUE          │  ← Current value
└────────────────┘
```

### MQTT Topic Structure

| Topic | Description |
|-------|-------------|
| `opcua/lcd/data` | Real-time data messages |
| `opcua/lcd/metadata` | DataSet metadata (retained) |

### Example OPC UA JSON Message

```json
{
  "MessageId": "1",
  "MessageType": "ua-data",
  "PublisherId": "urn:esp32:lcd:demo",
  "Messages": [{
    "DataSetWriterId": 1,
    "SequenceNumber": 42,
    "Payload": {
      "DataType": "Float",
      "Value": 23.45,
      "DisplayLine1": "FLOAT #42",
      "DisplayLine2": "= 23.45"
    }
  }]
}
```

## Validation with OPC UA Tools

This example has been validated with:

- **Prosys OPC UA Browser** - JSON message visualization
- **OPC Labs OpcCmd** - Command-line subscriber testing
- **MQTT Explorer** - Raw message inspection

## File Structure

```
lcd_display/
├── README.md           # This file
├── README_PT.md        # Portuguese documentation
├── config_example.py   # Configuration template
├── boot.py             # WiFi initialization with LCD feedback
├── main.py             # Main application loop
├── opcua_micro.py      # Lightweight OPC UA PubSub library
├── lcd_i2c.py          # LCD I2C driver for PCF8574
└── simple_lcd.py       # Alternative simplified LCD driver
```

## Troubleshooting

### LCD not displaying

1. Check I2C connections (SDA, SCL)
2. Verify I2C address: common addresses are `0x27`, `0x3F`, `0x20`
3. Run I2C scanner:
   ```python
   import machine
   i2c = machine.I2C(0, scl=machine.Pin(22), sda=machine.Pin(21))
   print(i2c.scan())
   ```

### MQTT connection failed

1. Verify broker IP address and port
2. Check if broker is running: `mosquitto -v`
3. Test with MQTT client: `mosquitto_sub -h <broker_ip> -t "opcua/#" -v`

### WiFi not connecting

1. Verify SSID and password in `config.py`
2. Check signal strength
3. ESP32 supports 2.4GHz networks only

## Related Projects

- [opcua_pubsub_esp32](https://github.com/YOUR_USERNAME/opcua_pubsub_esp32) - Main OPC UA PubSub MicroPython library
- [MicroPython](https://micropython.org/) - Python for microcontrollers
- [OPC UA Specification](https://opcfoundation.org/developer-tools/specifications-unified-architecture) - Official IEC 62541 documentation

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the [LICENSE](../LICENSE) file for details.

## Author

Developed as part of research on OPC UA PubSub implementation for resource-constrained devices.

---

*This example is part of the OPC UA PubSub ESP32 project, demonstrating practical industrial IoT applications with MicroPython.*
