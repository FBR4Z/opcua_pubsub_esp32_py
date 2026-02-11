# OPC UA PubSub + Node-RED Bidirectional Example

A minimal bidirectional example: **1 bit in each direction** using OPC UA PubSub JSON encoding (IEC 62541-14) over MQTT.

```
  ESP32                          Node-RED Dashboard
┌──────────┐    OPC UA JSON    ┌──────────────────┐
│ [Button]─┼───────────────────►  🟢 PRESSED      │
│          │  opcua/.../button  │                  │
│          │                    │                  │
│  (LED)◄──┼────────────────────┤  [Switch ON/OFF] │
│          │  opcua/.../led/cmd │                  │
└──────────┘                    └──────────────────┘
```

Both directions use **real OPC UA PubSub NetworkMessages** — not plain MQTT payloads.

## Requirements

### Hardware
| Component | Pin | Notes |
|-----------|-----|-------|
| Push button | GPIO4 → GND | Internal pull-up enabled |
| LED | GPIO2 | Built-in LED on most ESP32 boards |

> **No button?** Touch a jumper wire from GPIO4 to GND to simulate a press.

### Software (PC)
| Software | Version | Purpose |
|----------|---------|---------|
| Mosquitto | 2.x | MQTT Broker |
| Node-RED | 4.x | Flow engine + Dashboard |
| @flowfuse/node-red-dashboard | 1.x | Dashboard UI widgets |

### Software (ESP32)
| File | Source | Description |
|------|--------|-------------|
| `opcua_pubsub.py` | `src/opcua_pubsub.py` | OPC UA PubSub library (with `parse_network_message`) |
| `main.py` | This folder | Example application |
| `config.py` | Copy from `config_example.py` | Your WiFi/MQTT settings |

## Setup

### 1. Configure ESP32

```bash
cp config_example.py config.py
# Edit config.py with your WiFi and broker IP
```

Upload to ESP32 (via Thonny or mpremote):
- `config.py`
- `main.py`
- `opcua_pubsub.py` (from `src/`, must include `parse_network_message`)

### 2. Import Node-RED Flow

1. Open Node-RED: `http://localhost:1880`
2. Menu **☰** → **Import**
3. Paste the contents of `flows.json`
4. Click **Import**
5. Click **Deploy** (red button, top right)

### 3. Open Dashboard

Navigate to `http://localhost:1880/dashboard`

### 4. Run ESP32

Reset the ESP32 or run `main.py` from Thonny. You should see:

```
[READY] Press button or toggle LED from Node-RED dashboard
```

## MQTT Topics

| Topic | Direction | Content |
|-------|-----------|---------|
| `opcua/json/nodered/button` | ESP32 → Node-RED | Button state (OPC UA JSON) |
| `opcua/json/nodered/led/cmd` | Node-RED → ESP32 | LED command (OPC UA JSON) |

### Message Format (ESP32 → Node-RED)

```json
{
  "MessageId": "1",
  "MessageType": "ua-data",
  "PublisherId": "ESP32-NodeRED-001",
  "Messages": [{
    "DataSetWriterId": 1001,
    "SequenceNumber": 1,
    "Payload": {
      "Button": {
        "Value": true,
        "SourceTimestamp": "2026-02-10T19:30:00Z"
      }
    }
  }]
}
```

### Message Format (Node-RED → ESP32)

```json
{
  "MessageId": "1",
  "MessageType": "ua-data",
  "PublisherId": "NodeRED-Dashboard",
  "Messages": [{
    "DataSetWriterId": 2001,
    "SequenceNumber": 1,
    "Payload": {
      "LED": {
        "Value": true,
        "SourceTimestamp": "2026-02-10T19:30:05.123Z"
      }
    }
  }]
}
```

## Library Modification

This example requires the `parse_network_message()` function added to `src/opcua_pubsub.py`. This function parses incoming OPC UA PubSub JSON NetworkMessages, enabling the ESP32 to act as both Publisher and Subscriber.

```python
from opcua_pubsub import parse_network_message

payload = parse_network_message(mqtt_message)
# payload = {"LED": {"Value": true, "SourceTimestamp": "..."}}
```

## Troubleshooting

### Dashboard shows "Cannot GET /dashboard"
Deploy the flow first (red Deploy button in Node-RED editor).

### ESP32 not receiving LED commands
1. Check Mosquitto is running: `net start mosquitto`
2. Verify broker IP in `config.py` matches your PC's IP
3. Test with: `mosquitto_sub -h localhost -t "opcua/json/nodered/#" -v`

### Button state not appearing in dashboard
1. Check ESP32 serial output for `[PUB]` messages
2. Verify MQTT connection in Node-RED (green dot under MQTT nodes)
3. Check debug sidebar in Node-RED editor (bug icon, right panel)
