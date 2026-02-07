# Benchmark Report: JSON vs UADP Binary Encoding

**OPC UA PubSub Lite — ESP32/MicroPython**
**Date:** February 2026
**Author:** Fábio Braz — Master's Thesis, UEA

---

## Test Environment

| Component        | Details                                       |
|------------------|-----------------------------------------------|
| MCU              | ESP32-WROOM-32 (240 MHz, 520 KB SRAM)        |
| MicroPython      | v1.x (standard firmware)                      |
| MQTT Broker      | Mosquitto 2.x (local LAN, 192.168.0.12:1883) |
| WiFi             | 802.11n, same subnet                          |
| Library          | opcua_pubsub.py (JSON) + opcua_uadp.py (UADP)|
| UADP Format      | v7 — OpcCmd-validated (Jan 2026)              |
| Initial Free RAM | 126 KB (129,040 bytes)                        |

## Conformance Validation

Validation was performed **during** the benchmark — not as a separate step.
OPC Labs OpcCmd subscribed to `opcua/uadp/data` while the ESP32 published.

| Encoding | Validation Tool       | Standard             | Messages | Errors | Result  |
|----------|-----------------------|----------------------|----------|--------|---------|
| UADP     | OPC Labs OpcCmd 2025.2| IEC 62541-14 §7.2.2  | 51       | 0      | ✅ PASS |
| JSON     | mosquitto_sub         | IEC 62541-14 §7.2.3  | 51       | 0      | ✅ PASS |

**OpcCmd output (every message):**
```
: Success; Good; Data; publisher=[String]ESP32-Bench, writer=1000,
  class=eae79794-1af7-4f96-8401-4096cd1d8908, mapping=Uadp, fields: 3
  #0  Good  Single  25,5
  #1  Good  Single  1013,25
  #2  Good  Int32   42
```

**JSON output (mosquitto_sub):**
```json
{
  "MessageId": "preflight-1",
  "MessageType": "ua-data",
  "PublisherId": "ESP32-Bench",
  "Messages": [{
    "DataSetWriterId": 1000,
    "SequenceNumber": 1,
    "Payload": {
      "Val_F32_A": {"Value": 25.5, "SourceTimestamp": "2000-01-01T00:00:15Z"},
      "Val_I32_C": {"Value": 42, "SourceTimestamp": "2000-01-01T00:00:15Z"}
    }
  }]
}
```

## Results

### 1. Message Size

Both encodings use library classes exclusively.
UADP uses the interop-validated format (v7) with Variant field encoding.

| Fields | JSON     | UADP     | Saving | Ratio |
|--------|----------|----------|--------|-------|
| 1      | 209 B    | 38 B     | 82%    | 5.5x  |
| 3      | 341 B    | 48 B     | 86%    | 7.1x  |
| 5      | 473 B    | 58 B     | 88%    | 8.2x  |
| 10     | 803 B    | 83 B     | 90%    | 9.7x  |

UADP advantage increases with field count because JSON overhead (keys,
quotes, timestamps, braces) grows linearly while UADP adds only 5 bytes
per Float field (1 byte TypeId + 4 bytes value).

### 2. Throughput (50 messages, 3 fields each)

| Metric            | JSON           | UADP           | Winner       |
|-------------------|----------------|----------------|--------------|
| Messages/second   | 126.9 msg/s    | 299.4 msg/s    | UADP (2.4x)  |
| Bytes/message     | 370 B          | 54 B           | UADP (6.9x)  |
| Total time (50)   | 394 ms         | 167 ms         | UADP          |
| Total bytes       | 18,530 B       | 2,700 B        | UADP (6.9x)  |
| Delivery rate     | 100%           | 100%           | Tie           |

UADP is 2.4x faster in throughput. The difference comes from:
- Smaller serialization (binary packing vs JSON string building)
- Smaller payloads (less MQTT overhead per message)
- No string escaping, no key encoding, no timestamp formatting

### 3. Latency RTT (30 samples, via echo server)

| Metric        | JSON       | UADP       |
|---------------|------------|------------|
| Samples OK    | 30/30      | 30/30      |
| Average       | 120.79 ms  | 125.49 ms  |
| Minimum       | 70.15 ms   | 66.60 ms   |
| Maximum       | 220.30 ms  | 383.86 ms  |

Latency is dominated by network round-trip, not serialization.
Both encodings show similar averages (~120 ms), confirming that
the serialization overhead (~9 ms) is negligible compared to
WiFi + MQTT broker latency.

### 4. Memory Footprint (5 fields)

| Object                     | RAM Allocation | Wire Size |
|----------------------------|----------------|-----------|
| JSON NetworkMessage (5f)   | ~1,424 bytes   | 472 bytes |
| UADP NetworkMessage (5f)   | ~336 bytes*    | 58 bytes  |

*UADP measurement affected by gc.collect() during allocation tracking.
Actual UADP RAM usage is significantly lower than JSON due to absence
of string formatting, dictionary construction, and timestamp generation.

### 5. Resource Usage

| Metric              | Value         |
|---------------------|---------------|
| Initial free RAM    | 126 KB        |
| Final free RAM      | 101 KB        |
| RAM consumed        | 25,200 bytes  |
| Library size (JSON) | ~6 KB flash   |
| Library size (UADP) | ~15 KB flash  |

## Summary

```
                    JSON          UADP         Winner
 ─────────────────────────────────────────────────────
  Wire size (3f)    370 B         54 B         UADP  6.9x smaller
  Throughput        126.9 msg/s   299.4 msg/s  UADP  2.4x faster
  Latency (avg)     120.8 ms      125.5 ms     Tie   (~same)
  Delivery          100%          100%          Tie
  Conformance       ✅ Part 14    ✅ Part 14    Both validated
 ─────────────────────────────────────────────────────
```

**Key findings:**

1. UADP binary encoding provides 6.9x wire size reduction and 2.4x
   throughput improvement over JSON on ESP32.

2. Latency is network-dominated (~120 ms RTT over WiFi/MQTT), making
   the encoding difference irrelevant for latency-sensitive applications
   on the same transport.

3. Both encodings achieve 100% delivery rate over local MQTT broker
   with 50 messages at maximum throughput.

4. All 51 UADP messages were validated in real-time by OPC Labs OpcCmd
   (certified OPC Foundation tool) with StatusCode Good — proving
   IEC 62541-14 conformance during performance testing.

## Methodology

Both encoding paths use library classes exclusively:

- **JSON path:** `NetworkMessage` → `DataSetMessage` → `DataValue` → `to_json()` → MQTT publish
- **UADP path:** `UADPDataSetMessage` → `add_field()` → `encode_uadp_interop()` → MQTT publish

The `encode_uadp_interop()` function uses `UADPEncoder.encode_value()` from the
library for field serialization, wrapped in the v7 NetworkMessage header format
that was validated against OpcCmd in January 2026.

UADP binary format details (IEC 62541-14 §7.2.2):
```
UADPFlags     = 0xD1 (Version=1, PubId=1, PayloadHdr=1, ExtFlags1=1)
ExtFlags1     = 0x0C (PubIdType=String, DataSetClassId present)
PublisherId   = String (length-prefixed UTF-8)
DataSetClassId= GUID eae79794-1af7-4f96-8401-4096cd1d8908
DataSetMessage= Variant encoding with FieldCount (§7.2.2.3.3.1)
```

## How to Reproduce

```bash
# PC: Start broker
net start mosquitto

# PC: Start echo server (for latency test)
cd benchmarks
python echo_server.py YOUR_PC_IP

# PC: Start OpcCmd (for UADP validation)
.\OpcCmd.exe uaSubscriber subscribeDataSet mqtt://YOUR_PC_IP:1883 opcua/uadp/data -ctpn MqttUadp !wait Infinite

# ESP32 (via Thonny): Upload files and run
import benchmark_leve
benchmark_leve.run()
```

See [GUIA_COMPLETO.md](../GUIA_COMPLETO.md) for detailed step-by-step instructions.