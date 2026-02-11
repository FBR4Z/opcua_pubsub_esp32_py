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

<p align="center">
  🇧🇷 <a href="README_PT.md">Versão em Português</a>
</p>

---

## Overview

This project implements the **OPC UA PubSub** protocol (IEC 62541-14) in **MicroPython** for **ESP32** microcontrollers. It provides both **JSON** and **UADP binary** encoding over **MQTT** transport, validated with certified OPC Foundation tools.

The library is designed for industrial brownfield retrofit scenarios where adding OPC UA connectivity to low-cost sensors can reduce per-node costs from €500–2000 (traditional PLCs) to €30–80 (ESP32 + this library).

---

## Performance Benchmarks

Tested on ESP32-WROOM-32 (240 MHz, MicroPython), local Mosquitto broker, February 2026:

| Metric | JSON | UADP Binary |
|--------|------|-------------|
| **Throughput** | 126.9 msg/s | 299.4 msg/s |
| **Message size** (3 fields) | 370 B | 54 B |
| **Latency RTT** (avg) | 120.8 ms | 125.5 ms |
| **Delivery rate** | 100% | 100% |
| **Wire efficiency** | 1.0x | 6.9x smaller |

UADP is **2.4x faster** and **6.9x smaller** on the wire. Latency is network-dominated (~120 ms WiFi/MQTT RTT), making the encoding difference negligible for individual messages.

All 51 UADP messages were validated in real-time by **OPC Labs OpcCmd** (certified OPC Foundation tool) during the benchmark — zero decoding errors, all StatusCode **Good**.

> Full report with methodology: [docs/BENCHMARK_REPORT.md](docs/BENCHMARK_REPORT.md)

---

## Encoding Formats

### JSON Encoding (IEC 62541-14 §7.2.3)

Human-readable format using standard JSON over MQTT. Ideal for debugging, prototyping, and environments where readability matters more than bandwidth. Compatible with any MQTT client that can parse JSON — no OPC UA-specific tooling required on the subscriber side.

```json
{
  "MessageType": "ua-data",
  "PublisherId": "ESP32-Sensor",
  "Messages": [{
    "DataSetWriterId": 1000,
    "SequenceNumber": 1,
    "Payload": {
      "Temperature": {"Value": 25.5, "SourceTimestamp": "2026-02-07T10:30:00Z"}
    }
  }]
}
```

### UADP Binary Encoding (IEC 62541-14 §7.2.2)

Compact binary format using the Variant field encoding defined in Part 14. Validated byte-by-byte against OPC Labs OpcCmd. Best suited for bandwidth-constrained networks and high-frequency data acquisition where every byte counts.

The implementation uses the v7 NetworkMessage header format with ExtendedFlags1, String PublisherId, DataSetClassId (GUID), and FieldCount — all mandatory for interoperability with certified OPC UA tools.

---

## OPC UA Part 14 Compliance

This implementation targets a **functional subset** of IEC 62541-14 suitable for resource-constrained devices. The table below maps each Part 14 profile to its implementation status.

### Implemented Profiles

| Profile | Part 14 Reference | Status | Notes |
|---------|-------------------|--------|-------|
| **PubSub Connection** | §6.2 | ✅ Full | MQTT broker connection, topic-based routing |
| **JSON NetworkMessage** | §7.2.3 | ✅ Full | MessageType, PublisherId, DataSetWriterId, Payload with DataValue (Value + SourceTimestamp). Validated with Prosys OPC UA Browser |
| **UADP NetworkMessage** | §7.2.2 | ✅ Full | UADPFlags, ExtendedFlags1, String PublisherId, DataSetClassId, PayloadHeader, Variant field encoding with FieldCount (§7.2.2.3.3.1). Validated with OPC Labs OpcCmd |
| **DataSetMessage (KeyFrame)** | §7.2.2.3 | ✅ Full | KeyFrame messages with sequence numbers. Both JSON and UADP |
| **MQTT Transport** | Annex B | ✅ Full | QoS 0/1 over MQTT 3.1.1. Tested with Mosquitto, HiveMQ Cloud |
| **Multiple DataTypes** | Part 6 | ✅ Full | Boolean, SByte, Byte, Int16, UInt16, Int32, UInt32, Int64, UInt64, Float, Double, String, DateTime, GUID, ByteString |
| **SecurityMode None** | §5.3.3.4 | ✅ Full | Appropriate for segregated industrial networks. TLS at MQTT transport layer available via broker configuration |

### Partially Implemented

| Profile | Part 14 Reference | Status | What's Missing |
|---------|-------------------|--------|----------------|
| **DataSetMessage (Delta)** | §7.2.2.3.2 | ⚠️ Partial | KeyFrame only. DeltaFrame encoding (changed fields only) not yet implemented. Feasible — requires field-level change tracking |
| **StatusCode in DataValue** | Part 4 | ⚠️ Partial | StatusCode class exists with Good/Bad/Uncertain codes. Not yet transmitted in UADP messages. JSON includes it as part of DataValue |
| **Subscriber Role** | §6.2.7 | ⚠️ Partial | UADP subscriber parsing available (`UADPSubscriber`, `UADPNetworkMessage.decode()`) but not integrated into high-level API |

### Not Implemented

| Profile | Part 14 Reference | Feasible on ESP32? | What Would Be Needed |
|---------|-------------------|--------------------|----------------------|
| **Discovery** | §6.4 | ⚠️ Limited | |
| **MetaData Message** | §7.2.4 | ✅ Yes | DataSetMetaData (field names, types, descriptions) as separate NetworkMessage. Adds ~2KB RAM. Planned for future version |
| **Security Sign** | §5.3.3.4 | ❌ No | Message-level signing (SHA-256 + RSA/ECC) exceeds ESP32 RAM for key storage and crypto operations. Use TLS at transport layer instead |
| **Security Sign & Encrypt** | §5.3.3.4 | ❌ No | AES-256-GCM + RSA key exchange. Same ESP32 constraints. TLS provides equivalent protection at transport layer |
| **UDP Transport** | Annex A | ❌ No | UDP multicast requires raw socket access not available in MicroPython's networking stack. Would need C module or different firmware |
| **AMQP Transport** | Annex C | ❌ No | AMQP 1.0 client library does not exist for MicroPython |
| **DataSetMessage (Event)** | §7.2.2.3.4 | ✅ Yes | Event-type messages for alarms/conditions. Not prioritized — most sensor nodes publish periodic data, not events |
| **WriterGroup / ReaderGroup** | §6.2.4 | ⚠️ Limited | Formal group configuration objects not implemented. Single-writer publishing works. Multi-writer would need group management logic (~3KB RAM) |

### Interoperability Validation

| Tool | Vendor | Encoding | Transport | Result |
|------|--------|----------|-----------|--------|
| **OPC Labs OpcCmd** | OPC Labs | UADP Binary | MQTT | ✅ 51/51 messages decoded, StatusCode Good |
| **Prosys OPC UA Browser** | Prosys OPC | JSON | MQTT | ✅ All messages parsed correctly |
| **MQTT Explorer** | Thomas Nordquist | JSON | MQTT | ✅ Structure validated |
| **mosquitto_sub** | Eclipse | Both | MQTT | ✅ Message delivery confirmed |

---

## Quick Start

### 1. Hardware

- ESP32 development board (any variant with WiFi)
- WiFi network (2.4 GHz)
- MQTT Broker (Mosquitto recommended)

### 2. Installation

```bash
git clone https://github.com/FBR4Z/opcua_pubsub_esp32_py.git
cd opcua_pubsub_esp32_py
```

Copy the library files from `src/` to the ESP32 using [Thonny](https://thonny.org/) or [mpremote](https://docs.micropython.org/en/latest/reference/mpremote.html).

### 3. Configuration

Create `config.py` on the ESP32 (use `config_example.py` as template):

```python
WIFI_SSID = "your_network"
WIFI_PASSWORD = "your_password"
MQTT_BROKER = "192.168.1.100"
MQTT_PORT = 1883
```

### 4. Publish JSON

```python
from opcua_pubsub import NetworkMessage, DataSetMessage, DataValue
from umqtt.simple import MQTTClient

mqtt = MQTTClient("ESP32", "192.168.1.100", 1883)
mqtt.connect()

nm = NetworkMessage(publisher_id="ESP32-Sensor", message_id="1")
dm = DataSetMessage(dataset_writer_id=1000, sequence_number=1)
dm.add_value("Temperature", DataValue(25.5))
dm.add_value("Pressure", DataValue(1013.25))
nm.add_dataset_message(dm)

mqtt.publish("opcua/json/data", nm.to_json())
```

### 5. Publish UADP Binary

```python
from opcua_uadp import UADPNetworkMessage, UADPDataSetMessage, OPCUATypes

msg = UADPNetworkMessage("ESP32-Sensor")
ds = UADPDataSetMessage(dataset_writer_id=1000, sequence_number=1)
ds.add_field("Temperature", 25.5, OPCUATypes.FLOAT)
ds.add_field("Pressure", 1013.25, OPCUATypes.FLOAT)
msg.add_dataset_message(ds)

mqtt.publish("opcua/uadp/data", msg.encode())
```

---

## Project Structure

```
opcua_pubsub_esp32_py/
├── README.md                       # This file
├── README_PT.md                    # Portuguese version
├── config_example.py               # Configuration template (copy to config.py)
├── .gitignore
│
├── src/                            # Core library
│   ├── opcua_pubsub.py             # Full JSON encoding: NetworkMessage, DataSetMessage,
│   │                               #   DataValue with StatusCode, OPCUAPublisher (Part 14 §7.2.3)
│   ├── opcua_uadp.py               # UADP binary encoding: UADPNetworkMessage, UADPDataSetMessage,
│   │                               #   UADPPublisher, UADPSubscriber, encoder/decoder (Part 14 §7.2.2)
│   └── opcua_micro.py              # Minimal version: DataValue, NetworkMessage.create_json(),
│                                   #   ESPTransport — smallest RAM footprint
│
├── examples/
│   ├── main.py                     # Simple JSON publisher using opcua_micro
│   └── lcd_display/                # LCD 16x2 I2C example with data type cycling
│       ├── main.py                 # Application loop with LCD feedback
│       ├── boot.py                 # WiFi init with LCD status display
│       ├── lcd_i2c.py              # LCD I2C driver (PCF8574/HD44780)
│       ├── opcua_micro.py          # Enhanced standalone lib (adds metadata, auth, QoS, retain)
│       ├── config_example.py       # LCD-specific config template
│       ├── .gitignore              # Ignores config.py with credentials
│       ├── README.md               # Example documentation (EN)
│       └── README_PT.md            # Example documentation (PT)
│
├── benchmarks/                     # Performance comparison suite
│   ├── benchmark_leve.py           # JSON vs UADP benchmark (runs on ESP32)
│   └── echo_server.py             # PC-side echo server for latency RTT measurement
│
└── docs/
    └── BENCHMARK_REPORT.md         # Full benchmark results and methodology
```

---

## Documentation

- **[docs/BENCHMARK_REPORT.md](docs/BENCHMARK_REPORT.md)** — Complete benchmark: message size, throughput, latency, memory. Includes OpcCmd validation proof and reproduction instructions.
- **[examples/lcd_display/README.md](examples/lcd_display/README.md)** — LCD example wiring, setup, and usage guide.

---

## Target Applications

This implementation is optimized for specific industrial IoT scenarios:

| Application | Suitability | Notes |
|-------------|-------------|-------|
| Environmental monitoring | ✅ Excellent | Temperature, humidity, air quality |
| Brownfield retrofitting | ✅ Excellent | Adding connectivity to legacy equipment |
| Rapid prototyping | ✅ Excellent | Quick proof-of-concept development |
| Asset tracking | ✅ Good | Location and status updates |
| Predictive maintenance | ✅ Good | Vibration, current monitoring |
| Real-time control | ❌ Not suitable | MicroPython GC introduces 15–50 ms jitter |

---

## Research Context

This project is part of a **Master's thesis** in Electrical Engineering at **Universidade do Estado do Amazonas (UEA)**, Brazil. The research addresses the gap in Python-based OPC UA PubSub implementations — as of 2026, no other MicroPython or Python implementation of IEC 62541-14 exists for resource-constrained devices.

---

## License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.

---

## Contact

**Fábio Braz** — Master's student, Electrical Engineering, UEA

- GitHub: [@FBR4Z](https://github.com/FBR4Z)
- LinkedIn: [linkedin.com/in/fábio-braz-2b0a6ab8](https://linkedin.com/in/fábio-braz-2b0a6ab8)
- Email: eng.f.braz@gmail.com

---
