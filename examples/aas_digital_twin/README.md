# OPC UA PubSub → Asset Administration Shell (AAS) Example

A practical demonstration of the OPC UA PubSub library feeding an Asset Administration Shell (AAS) digital twin of a robotic cell, using Eclipse BaSyx Python SDK.

```
  ESP32 IT (MicroPython)              PC (Python)
┌───────────────────────┐    MQTT    ┌──────────────────────────┐
│ opcua_pubsub.py       │──────────►│ aas_gateway.py           │
│ (IEC 62541-14 JSON)   │           │ (BaSyx Python SDK)       │
│                       │           │                          │
│ Simulates:            │           │ Creates AAS with:        │
│  • 4DOF arm joints    │           │  • Nameplate             │
│  • Conveyor belt      │           │  • OperationalData       │
│  • Piece detection    │           │  • OPCUAPubSubInfo       │
│  • Pick-and-place     │           │                          │
│    cycle              │           │ Exports: .aasx + .json   │
└───────────────────────┘           └──────────────────────────┘
                                              │
                                              ▼
                                    AASX Package Explorer
                                    (AAS V3 visualization)
```

## Architecture

The example demonstrates the **IT layer** of an OT/IT separated industrial architecture:

- **ESP32 IT** publishes operational data as OPC UA PubSub JSON messages (IEC 62541-14 §7.2.3) over MQTT
- **AAS Gateway** subscribes to the MQTT topic, parses the OPC UA PubSub NetworkMessages, and populates an AAS using the Eclipse BaSyx Python SDK
- The AAS is exported as `.aasx` (IDTA standard) and `.json`, viewable in the AASX Package Explorer

The OPC UA PubSub library (`opcua_pubsub.py`) is the central interoperability layer — it standardizes shop floor data into IEC 62541-14 format, enabling any compliant consumer (AAS, SCADA, dashboard) to interpret the data without prior knowledge of the source.

## AAS Structure

| Submodel | Contents |
|----------|----------|
| **Nameplate** | Manufacturer, asset type, communication protocol, OT/IT separation method |
| **OperationalData** | JointBase, JointShoulder, JointElbow, JointGripper (rad), ConveyorRunning, PieceDetected (bool), CycleCount, LastUpdate |
| **OPCUAPubSubInfo** | PublisherId, MQTT topic, encoding, MessageType, DataSetWriterId, MessagesReceived |

## Requirements

### Hardware
| Component | Description |
|-----------|-------------|
| ESP32 | Any ESP32 variant with WiFi |
| PC | Windows/Linux with Python 3.10+ |

### Software (ESP32)
| File | Source | Description |
|------|--------|-------------|
| `opcua_pubsub.py` | `src/opcua_pubsub.py` | OPC UA PubSub library |
| `main.py` | This folder | Robotic cell simulator + publisher |
| `config.py` | Copy from `config_example.py` | WiFi/MQTT credentials |

### Software (PC)
| Package | Version | Purpose |
|---------|---------|---------|
| basyx-python-sdk | ≥2.0.0 | AAS metamodel + AASX export |
| paho-mqtt | ≥2.0.0 | MQTT subscription |
| AASX Package Explorer | V3.x | AAS visualization (optional) |
| Mosquitto | 2.x | MQTT broker |

## Setup

### 1. Install PC dependencies

```bash
pip install basyx-python-sdk paho-mqtt
```

### 2. Configure ESP32

```bash
cp config_example.py config.py
# Edit config.py with your WiFi and broker IP
```

Upload to ESP32 (via Thonny or mpremote):
- `config.py`
- `main.py`
- `opcua_pubsub.py` (from `src/`)

### 3. Start Mosquitto broker

Ensure Mosquitto is running on your PC (port 1883).

### 4. Run AAS Gateway

```bash
python aas_gateway.py
```

The gateway will:
1. Create the initial AAS structure
2. Connect to MQTT and subscribe to `it/opcua/celula_robotica`
3. Update the AAS with each incoming OPC UA PubSub message
4. Export `celula_robotica.aasx` and `celula_robotica_aas.json` periodically

### 5. Reset ESP32

The ESP32 will start publishing simulated robotic cell data.

### 6. View AAS

Download [AASX Package Explorer](https://github.com/eclipse-aaspe/package-explorer/releases) and open `celula_robotica.aasx`.

## OPC UA PubSub Message Example

The ESP32 IT publishes messages in this format:

```json
{
  "MessageId": "42",
  "MessageType": "ua-data",
  "PublisherId": "urn:uea:celula-robotica:esp32-it",
  "Messages": [{
    "DataSetWriterId": 2000,
    "SequenceNumber": 42,
    "Payload": {
      "JointBase": {"Value": 0.785, "SourceTimestamp": "2026-04-20T15:00:00Z"},
      "JointShoulder": {"Value": -0.2, "SourceTimestamp": "2026-04-20T15:00:00Z"},
      "JointElbow": {"Value": 0.7, "SourceTimestamp": "2026-04-20T15:00:00Z"},
      "JointGripper": {"Value": 0.5, "SourceTimestamp": "2026-04-20T15:00:00Z"},
      "ConveyorRunning": {"Value": false, "SourceTimestamp": "2026-04-20T15:00:00Z"},
      "PieceDetected": {"Value": true, "SourceTimestamp": "2026-04-20T15:00:00Z"},
      "CycleCount": {"Value": 3, "SourceTimestamp": "2026-04-20T15:00:00Z"}
    }
  }]
}
```

## Data Type Mapping

The AAS Gateway performs the conversion between OPC UA types (Part 6) and AAS/XSD types:

| OPC UA Type | AAS (XSD) Type | Fields |
|-------------|----------------|--------|
| Float | xs:double | JointBase, JointShoulder, JointElbow, JointGripper |
| Boolean | xs:boolean | ConveyorRunning, PieceDetected |
| Integer | xs:integer | CycleCount |
| String | xs:string | LastUpdate |

## Research Context

This example is part of a **Master's dissertation** in Electrical Engineering at **UEA (Universidade do Estado do Amazonas)**, Brazil. It demonstrates the OPC UA PubSub library as the interoperability layer between the shop floor (OT) and the digital twin (IT), following OT/IT separation principles from IEC 62443.

## License

MIT License — see [LICENSE](../../LICENSE) for details.