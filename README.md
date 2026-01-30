# OPC UA PubSub for ESP32 (MicroPython)

<p align="center">
  <img src="https://img.shields.io/badge/OPC%20UA-Part%2014-blue?style=for-the-badge" alt="OPC UA Part 14"/>
  <img src="https://img.shields.io/badge/MicroPython-1.20+-green?style=for-the-badge" alt="MicroPython"/>
  <img src="https://img.shields.io/badge/ESP32-Supported-orange?style=for-the-badge" alt="ESP32"/>
  <img src="https://img.shields.io/badge/License-MIT-yellow?style=for-the-badge" alt="License"/>
</p>

<p align="center">
  <strong>The first MicroPython implementation of OPC UA PubSub (IEC 62541-14)</strong><br>
  Enabling industrial IoT on resource-constrained devices
</p>

---

## 🎯 Overview

This project implements the **OPC UA PubSub** protocol (IEC 62541-14) in **MicroPython** for **ESP32** microcontrollers. It enables low-cost devices to participate in industrial IoT networks using the standard OPC UA communication protocol.

### Key Achievement

| Metric | Traditional C Implementation | This Implementation |
|--------|------------------------------|---------------------|
| Memory Footprint | 2-4 MB | **~30 KB** |
| Reduction | - | **98.5%** |
| Hardware Cost | €500-2000 | **€30-80** |

### Validated Interoperability

---

## 📊 Performance Benchmarks

Tested on ESP32 (240MHz dual-core, MicroPython v1.27.0):

| Category | Metric | Value |
|----------|--------|-------|
| **Memory** | Library footprint | ~30 KB |
| **Throughput** | Publication rate | 8.67 msg/s |
| **Latency** | Average RTT | 161.89 ms |
| **Jitter** | RTT std deviation | 89.68 ms |
| **Reliability** | Message loss rate | **0%** |

> 📄 Full benchmark report: [BENCHMARK_REPORT.md](BENCHMARK_REPORT.md)

---

## ✨ Features

### Encoding Formats
- ✅ **JSON Encoding** - Human-readable, debuggable, wide compatibility
- ✅ **UADP Binary Encoding** - Compact, efficient for bandwidth-constrained networks

### Transport
- ✅ **MQTT** - Standard broker connectivity (Mosquitto, HiveMQ, etc.)

### OPC UA Compliance
- ✅ NetworkMessage structure (Part 14)
- ✅ DataSetMessage with sequence numbers
- ✅ DataValue with timestamps and StatusCodes
- ✅ Multiple data types (Boolean, Int16, UInt16, Int32, Float, Double, String, DateTime)
- ✅ Publisher and Subscriber roles

---

## 🚀 Quick Start

### 1. Hardware Requirements

- ESP32 development board (any variant)
- WiFi network (2.4 GHz)
- MQTT Broker (local or cloud)

### 2. Installation

```bash
# Clone the repository
git clone https://github.com/YOUR_USERNAME/opcua_pubsub_esp32.git
cd opcua_pubsub_esp32

# Copy files to ESP32 using Thonny or mpremote
# Required files: opcua_pubsub.py, config.py, main.py
```

### 3. Configuration

Create `config.py` from the template:

```python
# WiFi
WIFI_SSID = "your_network"
WIFI_PASSWORD = "your_password"

# MQTT Broker
MQTT_BROKER = "192.168.1.100"
MQTT_PORT = 1883

# OPC UA
PUBLISHER_ID = "ESP32-OPCUA-001"
```

### 4. Run

```python
import main
main.main()
```

---

## 📁 Project Structure

```
opcua_pubsub_esp32/
├── opcua_pubsub.py          # Main library (JSON encoding)
├── opcua_uadp.py            # UADP binary encoding
├── main.py                  # Example publisher
├── subscriber_example.py    # Example subscriber
├── config.py                # Configuration (create from template)
├── boot_wifi.py             # WiFi connection helper
│
├── examples/
│   └── lcd_display/         # LCD feedback example
│       ├── README.md
│       ├── main.py
│       ├── lcd_i2c.py
│       └── ...
│
├── benchmarks/
│   ├── benchmark_performance.py
│   ├── benchmark_json_vs_uadp.py
│   └── latency_echo_server.py
│
└── docs/
    ├── BENCHMARK_REPORT.md
    └── ROADMAP_OPC_UA_PUBSUB.md
```

---

## 💻 Usage Examples

### Publisher (JSON)

```python
from opcua_pubsub import OPCUAPublisher, DataValue, StatusCode
from umqtt.simple import MQTTClient

# Setup MQTT
mqtt = MQTTClient("esp32-pub", "192.168.1.100")
publisher = OPCUAPublisher("urn:esp32:sensor", mqtt)
publisher.connect()

# Publish sensor data
data = {
    "Temperature": DataValue(23.5),
    "Humidity": DataValue(65.0),
    "Status": DataValue("OK")
}
publisher.publish(dataset_writer_id=1, data_dict=data)
```

### Publisher with Quality Codes

```python
from opcua_pubsub import StatusCode

# Publish with explicit quality information
data_with_quality = {
    "Temperature": (23.5, StatusCode.GOOD),
    "Pressure": (-1, StatusCode.BAD_SENSOR_FAILURE),
    "Flow": (100.5, StatusCode.UNCERTAIN)
}
publisher.publish_with_quality(1, data_with_quality)
```

### JSON Message Output

```json
{
  "MessageId": "1",
  "MessageType": "ua-data",
  "PublisherId": "urn:esp32:sensor",
  "Messages": [{
    "DataSetWriterId": 1,
    "SequenceNumber": 1,
    "Payload": {
      "Temperature": {
        "Value": 23.5,
        "SourceTimestamp": "2024-01-15T10:30:00Z"
      },
      "Humidity": {
        "Value": 65.0,
        "SourceTimestamp": "2024-01-15T10:30:00Z"
      }
    }
  }]
}
```

---

## 🎯 Target Applications

This implementation is optimized for specific industrial IoT scenarios:

| Application | Suitability | Notes |
|-------------|-------------|-------|
| Environmental monitoring | ✅ Excellent | Temperature, humidity, air quality |
| Brownfield retrofitting | ✅ Excellent | Adding connectivity to legacy equipment |
| Rapid prototyping | ✅ Excellent | Quick proof-of-concept development |
| Asset tracking | ✅ Good | Location and status updates |
| Predictive maintenance | ✅ Good | Vibration, current monitoring |
| Real-time control | ❌ Not suitable | MicroPython GC introduces 15-50ms jitter |

---

## 📚 Documentation

- [Benchmark Report](BENCHMARK_REPORT.md) - Detailed performance analysis
- [UADP Interoperability](UADP_INTEROPERABILIDADE_OPCMD.md) - Binary encoding validation
- [Roadmap](ROADMAP_OPC_UA_PUBSUB.md) - Future development plans

---

## 🔬 Research Context

This project is part of a Master's thesis at **Universidade do Estado do Amazonas (UEA)**, Brazil, investigating the viability of OPC UA PubSub on resource-constrained microcontrollers.

### Research Contributions

1. **First MicroPython implementation** of OPC UA PubSub (IEC 62541-14)
2. **98.5% memory reduction** compared to traditional C implementations
3. **Validated interoperability** with certified commercial tools
4. **Comprehensive benchmarks** for industrial IoT scenarios

---

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

### Areas for Contribution

- [ ] Security layer implementation (Part 14 security modes)
- [ ] Additional transport protocols (UDP, AMQP)
- [ ] Discovery mechanisms for broker-based PubSub
- [ ] Support for other microcontrollers (RP2040, STM32)
- [ ] Web-based configuration interface

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 📧 Contact

For questions about this research or collaboration opportunities, please open an issue or reach out via LinkedIn.

---

<p align="center">
  <sub>Built with ❤️ for the Industrial IoT community</sub>
</p>
