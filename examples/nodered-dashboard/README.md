# OPC UA PubSub + Node-RED Full Dashboard

Bidirectional OPC UA PubSub (IEC 62541-14) demo with sensors, actuators, gauges, and charts.

```
  ESP32 (MicroPython)              Node-RED Dashboard
┌──────────────────────┐         ┌──────────────────────┐
│ [Button GPIO4]───────┼────────►│ 🟢 State indicator   │
│ [DHT11  GPIO13]──────┼────────►│ 🌡️ Temp gauge+chart  │
│                      ├────────►│ 💧 Humid gauge+chart │
│ [Pot    GPIO34]──────┼────────►│ 📊 Pot gauge (0-100%)│
│                      │         │                      │
│ [LED    GPIO15] ◄────┼─────── │ 🔘 Switch ON/OFF     │
│ [Servo  GPIO18] ◄────┼─────── │ 🎚️ Slider 0-180°     │
└──────────────────────┘         └──────────────────────┘
         All messages use OPC UA PubSub JSON encoding
```

## Hardware

| Component | GPIO | Direction | Notes |
|-----------|------|-----------|-------|
| Push button | 4 | ESP32 → Dashboard | Internal pull-up, connect to GND |
| LED | 15 | Dashboard → ESP32 | 220Ω resistor to GND |
| DHT11 | 13 | ESP32 → Dashboard | 3-pin module (built-in pull-up) |
| Servo SG90 | 18 | Dashboard → ESP32 | Signal pin; power from VIN (5V) |
| Potentiometer | 34 | ESP32 → Dashboard | Wiper to GPIO34, ends to 3.3V and GND |

### Wiring

```
ESP32-WROOM-32
┌────────────────────┐
│               GPIO4 ├──── Button ──── GND
│              GPIO15 ├──── R220Ω ──── LED ──── GND
│              GPIO13 ├──── DHT11 Data
│              GPIO18 ├──── Servo signal (orange wire)
│              GPIO34 ├──── Potentiometer wiper (middle pin)
│                 3V3 ├──── DHT11 VCC + Pot pin 1
│                 GND ├──── DHT11 GND + Pot pin 3 + Servo GND (brown)
│                 VIN ├──── Servo VCC (red wire, 5V)
└────────────────────┘
```

> **No button?** Touch a jumper wire from GPIO4 to GND.
> **Servo unstable?** Use external 5V supply (share GND with ESP32).

## Software Requirements

### PC
| Software | Install |
|----------|---------|
| Mosquitto | `net start mosquitto` |
| Node-RED | `node-red` (in terminal) |
| Dashboard | Manage Palette → Install `@flowfuse/node-red-dashboard` |

### ESP32 Files
| File | Source |
|------|--------|
| `main.py` | This folder |
| `config.py` | Copy from `config_example.py` |
| `opcua_pubsub.py` | `src/opcua_pubsub.py` (with `parse_network_message`) |

## Setup

### 1. ESP32

```bash
cp config_example.py config.py
# Edit with your WiFi SSID, password, and PC broker IP
```

Upload via Thonny or mpremote: `config.py`, `main.py`, `opcua_pubsub.py`.

### 2. Node-RED

1. Start: `node-red` in terminal
2. Open `http://localhost:1880`
3. **Delete** old flows if any (tab → right click → Delete)
4. Menu **☰** → **Import** → paste `flows.json` → **Import** → **Deploy**
5. Open `http://localhost:1880/dashboard`

### 3. Run

Reset ESP32. Serial output:

```
[READY] Dashboard: http://<your-pc-ip>:1880/dashboard
[SNS] #1 T=26°C H=65% Pot=42.3% Servo=90° (287 B)
```

## MQTT Topics

| Topic | Direction | Content |
|-------|-----------|---------|
| `opcua/json/nodered/button` | ESP32 → Node-RED | Button state (on change) |
| `opcua/json/nodered/sensors` | ESP32 → Node-RED | DHT11 + Pot + Servo position (every 2s) |
| `opcua/json/nodered/cmd` | Node-RED → ESP32 | LED on/off, Servo angle |

### Sensor Message (ESP32 → Node-RED)

```json
{
  "MessageId": "5",
  "MessageType": "ua-data",
  "PublisherId": "ESP32-NodeRED-001",
  "Messages": [{
    "DataSetWriterId": 1002,
    "SequenceNumber": 5,
    "Payload": {
      "Temperature": {"Value": 26, "SourceTimestamp": "2026-02-11T10:00:00Z"},
      "Humidity": {"Value": 65, "SourceTimestamp": "2026-02-11T10:00:00Z"},
      "Potentiometer": {"Value": 42.3, "SourceTimestamp": "2026-02-11T10:00:00Z"},
      "ServoPosition": {"Value": 90, "SourceTimestamp": "2026-02-11T10:00:00Z"}
    }
  }]
}
```

### Command Message (Node-RED → ESP32)

```json
{
  "MessageId": "1",
  "MessageType": "ua-data",
  "PublisherId": "NodeRED-Dashboard",
  "Messages": [{
    "DataSetWriterId": 2001,
    "SequenceNumber": 1,
    "Payload": {
      "LED": {"Value": true, "SourceTimestamp": "2026-02-11T10:00:05Z"}
    }
  }]
}
```

## Troubleshooting

### DHT11 read errors
The DHT11 needs ~2s between reads. If you see `[DHT] Read error`, the interval is already handled — cached values are used until the next successful read.

### Servo jitters
Power issue. Connect servo VCC to an external 5V supply instead of ESP32 VIN. Keep GND shared.

### Dashboard shows no data
1. Check MQTT broker: `mosquitto_sub -h localhost -t "opcua/json/nodered/#" -v`
2. Check Node-RED debug sidebar (bug icon, right panel)
3. Verify ESP32 serial shows `[SNS]` lines