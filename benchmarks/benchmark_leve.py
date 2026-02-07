"""
Benchmark: JSON vs UADP Encoding
OPC UA PubSub Lite - ESP32/MicroPython

Compares JSON (Part 14 sec. 7.2.3) vs UADP Binary (Part 14 sec. 7.2.2)
encoding over the same MQTT transport.

Both encodings use the library classes exclusively.
Run OpcCmd (UADP) and/or Prosys (JSON) in parallel for conformance proof.

Author: Fabio
Project: Master's Thesis - UEA
Version: 2.1
"""

import gc
import time
import ustruct

# =============================================================================
# CONFIGURATION
# =============================================================================

try:
    import config
    WIFI_SSID = config.WIFI_SSID
    WIFI_PASSWORD = config.WIFI_PASSWORD
    MQTT_BROKER = config.MQTT_BROKER
    MQTT_PORT = getattr(config, 'MQTT_PORT', 1883)
except ImportError:
    WIFI_SSID = "YOUR_WIFI_SSID"
    WIFI_PASSWORD = "YOUR_WIFI_PASSWORD"
    MQTT_BROKER = "YOUR_PC_IP"
    MQTT_PORT = 1883

# MQTT topics
TOPIC_JSON      = "opcua/json/data"
TOPIC_UADP      = "opcua/uadp/data"
TOPIC_JSON_PING = "opcua/json/ping"
TOPIC_JSON_ECHO = "opcua/json/echo"
TOPIC_UADP_PING = "opcua/uadp/ping"
TOPIC_UADP_ECHO = "opcua/uadp/echo"

# DataSetClassId (registered during OpcCmd validation, Jan 2026)
DATASET_CLASS_ID = bytes([
    0x94, 0x97, 0xe7, 0xea, 0xf7, 0x1a, 0x96, 0x4f,
    0x84, 0x01, 0x40, 0x96, 0xcd, 0x1d, 0x89, 0x08
])

# Test payload values (NOT simulated sensor data - explicit benchmark values)
BENCH_VALS = {
    "Val_F32_A": (25.5,    "FLOAT"),   # Float A
    "Val_F32_B": (1013.25, "FLOAT"),   # Float B
    "Val_I32_C": (42,      "INT32"),   # Int32 C
}


# =============================================================================
# UADP INTEROP ENCODING (v7 format validated with OpcCmd)
# =============================================================================

def encode_uadp_interop(publisher_id, dataset_writer_id, fields):
    """
    Encodes UADP NetworkMessage in the interop-validated format.

    Uses UADPEncoder for field serialization + v7 NetworkMessage header
    validated against OPC Labs OpcCmd (certified OPC Foundation tool).

    Args:
        publisher_id: str - publisher name
        dataset_writer_id: int - writer ID
        fields: list of (name, value, type_id) tuples

    Returns:
        bytes - complete UADP NetworkMessage
    """
    from opcua_uadp import UADPEncoder, OPCUATypes

    buf = bytearray()

    # --- NetworkMessage Header (IEC 62541-14 sec. 7.2.2.2) ---
    buf.append(0xD1)  # UADPFlags
    buf.append(0x0C)  # ExtendedFlags1 (String PubId + DataSetClassId)

    # PublisherId (String)
    pub_bytes = publisher_id.encode('utf-8')
    buf.extend(ustruct.pack('<i', len(pub_bytes)))
    buf.extend(pub_bytes)

    # DataSetClassId (16 bytes GUID)
    buf.extend(DATASET_CLASS_ID)

    # --- Payload Header ---
    buf.append(0x01)  # 1 DataSetMessage
    buf.extend(ustruct.pack('<H', dataset_writer_id))

    # --- DataSetMessage (Variant encoding, sec. 7.2.2.3) ---
    buf.append(0x01)  # DataSetFlags1: Valid=1, FieldEncoding=Variant
    buf.extend(ustruct.pack('<H', len(fields)))  # FieldCount (sec. 7.2.2.3.3.1)

    for name, value, type_id in fields:
        buf.append(type_id)  # Variant TypeId
        buf.extend(UADPEncoder.encode_value(value, type_id))

    return bytes(buf)


# =============================================================================
# CONNECT
# =============================================================================

def connect():
    """Connects WiFi and MQTT. Returns MQTTClient or None."""
    import network
    from umqtt.simple import MQTTClient

    gc.collect()

    print("[1/2] Connecting WiFi...")
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    time.sleep(1)

    if not wlan.isconnected():
        wlan.connect(WIFI_SSID, WIFI_PASSWORD)
        for i in range(20):
            if wlan.isconnected():
                break
            print(".", end="")
            time.sleep(1)

    if not wlan.isconnected():
        print("\nERROR: WiFi failed!")
        return None

    print(f"\nIP: {wlan.ifconfig()[0]}")

    print("[2/2] Connecting MQTT...")
    mqtt = MQTTClient("ESP32-BENCH", MQTT_BROKER, MQTT_PORT)
    mqtt.connect()
    print(f"OK! Broker: {MQTT_BROKER}:{MQTT_PORT}")

    gc.collect()
    print(f"Free RAM: {gc.mem_free() // 1024} KB")
    return mqtt


# =============================================================================
# BENCHMARK 1: Message Size (offline)
# =============================================================================

def benchmark_size():
    """Compares message size: library JSON vs library UADP."""
    from opcua_pubsub import NetworkMessage, DataSetMessage, DataValue
    from opcua_uadp import OPCUATypes

    print(f"\n{'=' * 55}")
    print("MESSAGE SIZE: JSON (library) vs UADP (interop)")
    print('=' * 55)
    print(f"{'Fields':>6} | {'JSON':>8} | {'UADP':>8} | {'Saving':>7} | {'Ratio':>6}")
    print(f"{'-' * 6}-+-{'-' * 8}-+-{'-' * 8}-+-{'-' * 7}-+-{'-' * 6}")

    for nf in [1, 3, 5, 10]:
        # JSON via library
        nm = NetworkMessage("ESP32", "1")
        dm = DataSetMessage(1000, 1)
        for i in range(nf):
            dm.add_value(f"V{i}", DataValue(10.0 + i * 0.5))
        nm.add_dataset_message(dm)
        json_size = len(nm.to_json())

        # UADP via library + interop encoding
        fields = []
        for i in range(nf):
            fields.append((f"V{i}", 10.0 + i * 0.5, OPCUATypes.FLOAT))
        uadp_payload = encode_uadp_interop("ESP32", 1000, fields)
        uadp_size = len(uadp_payload)

        saving = (1 - uadp_size / json_size) * 100
        ratio = json_size / uadp_size
        print(f"{nf:>6} | {json_size:>7}B | {uadp_size:>7}B | {saving:>6.0f}% | {ratio:>5.1f}x")

    gc.collect()


# =============================================================================
# BENCHMARK 2: Memory Footprint (offline)
# =============================================================================

def benchmark_memory():
    """Measures memory consumption of library objects."""
    from opcua_pubsub import NetworkMessage, DataSetMessage, DataValue
    from opcua_uadp import OPCUATypes

    print(f"\n{'=' * 55}")
    print("MEMORY FOOTPRINT (5 fields)")
    print('=' * 55)

    # JSON
    gc.collect()
    m0 = gc.mem_alloc()
    nm = NetworkMessage("ESP32", "1")
    dm = DataSetMessage(1000, 1)
    for i in range(5):
        dm.add_value(f"V{i}", DataValue(i * 10.0))
    nm.add_dataset_message(dm)
    json_str = nm.to_json()
    gc.collect()
    m1 = gc.mem_alloc()
    print(f"  JSON  objects: ~{m1 - m0} bytes RAM | wire: {len(json_str)} bytes")
    nm = None; dm = None; json_str = None
    gc.collect()

    # UADP
    gc.collect()
    m0 = gc.mem_alloc()
    fields = [(f"V{i}", i * 10.0, OPCUATypes.FLOAT) for i in range(5)]
    uadp_bytes = encode_uadp_interop("ESP32", 1000, fields)
    gc.collect()
    m1 = gc.mem_alloc()
    print(f"  UADP objects: ~{m1 - m0} bytes RAM | wire: {len(uadp_bytes)} bytes")
    fields = None; uadp_bytes = None
    gc.collect()

    print(f"\n  Free RAM: {gc.mem_free() // 1024} KB")


# =============================================================================
# BENCHMARK 3: Throughput
# =============================================================================

def benchmark_throughput(mqtt, n=50):
    """
    Throughput: JSON vs UADP using library classes.
    OpcCmd on opcua/uadp/data validates UADP conformance.
    """
    from opcua_pubsub import NetworkMessage, DataSetMessage, DataValue
    from opcua_uadp import OPCUATypes

    print(f"\n{'=' * 55}")
    print(f"THROUGHPUT ({n} messages, 3 fields each)")
    print(f"  JSON -> {TOPIC_JSON}")
    print(f"  UADP -> {TOPIC_UADP}")
    print('=' * 55)

    va, vb, vc = 25.5, 1013.25, 42

    # --- JSON ---
    print("\n[JSON] NetworkMessage.to_json() -> MQTT publish")
    gc.collect()
    t0 = time.ticks_ms()
    bj = 0

    for i in range(n):
        nm = NetworkMessage("ESP32-Bench", str(i))
        dm = DataSetMessage(1000, i)
        dm.add_value("Val_F32_A", DataValue(va))
        dm.add_value("Val_F32_B", DataValue(vb))
        dm.add_value("Val_I32_C", DataValue(vc))
        nm.add_dataset_message(dm)
        payload = nm.to_json()
        mqtt.publish(TOPIC_JSON, payload)
        bj += len(payload)

    tj = time.ticks_diff(time.ticks_ms(), t0)
    rj = n / (tj / 1000) if tj > 0 else 0
    print(f"  {tj} ms | {rj:.1f} msg/s | {bj} B total ({bj // n} B/msg)")

    time.sleep(1)
    gc.collect()

    # --- UADP ---
    print("\n[UADP] encode_uadp_interop() -> MQTT publish")
    t0 = time.ticks_ms()
    bu = 0

    for i in range(n):
        fields = [
            ("Val_F32_A", va, OPCUATypes.FLOAT),
            ("Val_F32_B", vb, OPCUATypes.FLOAT),
            ("Val_I32_C", vc, OPCUATypes.INT32),
        ]
        payload = encode_uadp_interop("ESP32-Bench", 1000, fields)
        mqtt.publish(TOPIC_UADP, payload)
        bu += len(payload)

    tu = time.ticks_diff(time.ticks_ms(), t0)
    ru = n / (tu / 1000) if tu > 0 else 0
    print(f"  {tu} ms | {ru:.1f} msg/s | {bu} B total ({bu // n} B/msg)")

    ratio = bj / bu if bu > 0 else 0
    print(f"\n{'-' * 55}")
    print("THROUGHPUT SUMMARY:")
    print(f"  JSON: {rj:.1f} msg/s | {bj // n} B/msg")
    print(f"  UADP: {ru:.1f} msg/s | {bu // n} B/msg")
    print(f"  Wire ratio: UADP is {ratio:.1f}x smaller")

    return {
        "json": {"rate": rj, "bytes_per_msg": bj // n, "time_ms": tj},
        "uadp": {"rate": ru, "bytes_per_msg": bu // n, "time_ms": tu}
    }


# =============================================================================
# BENCHMARK 4: Latency RTT
# =============================================================================

def benchmark_latency(mqtt, n=30):
    """RTT latency. Requires echo_server.py on PC."""
    from opcua_pubsub import NetworkMessage, DataSetMessage, DataValue
    from opcua_uadp import OPCUATypes

    print(f"\n{'=' * 55}")
    print(f"LATENCY RTT ({n} samples)")
    print(f"  JSON: {TOPIC_JSON_PING} -> {TOPIC_JSON_ECHO}")
    print(f"  UADP: {TOPIC_UADP_PING} -> {TOPIC_UADP_ECHO}")
    print("  NOTE: Requires echo_server.py on PC!")
    print('=' * 55)

    results = {}
    echo_ok = False

    def on_echo(topic, msg):
        nonlocal echo_ok
        echo_ok = True

    # --- JSON RTT ---
    print("\n[JSON RTT]")
    rtts = []
    mqtt.set_callback(on_echo)
    mqtt.subscribe(TOPIC_JSON_ECHO)
    time.sleep(0.3)

    for i in range(n):
        nm = NetworkMessage("ESP32-Bench", str(i))
        dm = DataSetMessage(1000, i)
        dm.add_value("Seq", DataValue(i))
        nm.add_dataset_message(dm)

        echo_ok = False
        t0 = time.ticks_us()
        mqtt.publish(TOPIC_JSON_PING, nm.to_json())

        deadline = time.ticks_ms() + 2000
        while not echo_ok and time.ticks_ms() < deadline:
            mqtt.check_msg()
            time.sleep_ms(1)

        if echo_ok:
            rtts.append(time.ticks_diff(time.ticks_us(), t0))
        time.sleep_ms(50)

    if rtts:
        avg = sum(rtts) / len(rtts)
        results["json"] = {
            "ok": len(rtts), "avg_ms": avg / 1000,
            "min_ms": min(rtts) / 1000, "max_ms": max(rtts) / 1000
        }
        r = results["json"]
        print(f"  {r['ok']}/{n} OK | Avg: {r['avg_ms']:.2f} ms | "
              f"Min: {r['min_ms']:.2f} | Max: {r['max_ms']:.2f}")
    else:
        print("  ERROR: No echo! Is echo_server.py running?")
        results["json"] = {"error": "no echo"}

    gc.collect()
    time.sleep(0.5)

    # --- UADP RTT ---
    print("\n[UADP RTT]")
    rtts = []
    mqtt.set_callback(on_echo)
    mqtt.subscribe(TOPIC_UADP_ECHO)
    time.sleep(0.3)

    for i in range(n):
        fields = [("Seq", i, OPCUATypes.INT32)]
        payload = encode_uadp_interop("ESP32-Bench", 1000, fields)

        echo_ok = False
        t0 = time.ticks_us()
        mqtt.publish(TOPIC_UADP_PING, payload)

        deadline = time.ticks_ms() + 2000
        while not echo_ok and time.ticks_ms() < deadline:
            mqtt.check_msg()
            time.sleep_ms(1)

        if echo_ok:
            rtts.append(time.ticks_diff(time.ticks_us(), t0))
        time.sleep_ms(50)

    mqtt.set_callback(None)

    if rtts:
        avg = sum(rtts) / len(rtts)
        results["uadp"] = {
            "ok": len(rtts), "avg_ms": avg / 1000,
            "min_ms": min(rtts) / 1000, "max_ms": max(rtts) / 1000
        }
        r = results["uadp"]
        print(f"  {r['ok']}/{n} OK | Avg: {r['avg_ms']:.2f} ms | "
              f"Min: {r['min_ms']:.2f} | Max: {r['max_ms']:.2f}")
    else:
        print("  ERROR: No echo!")
        results["uadp"] = {"error": "no echo"}

    j = results.get("json", {})
    u = results.get("uadp", {})
    if j.get("avg_ms") and u.get("avg_ms"):
        print(f"\n{'-' * 55}")
        print(f"  JSON: {j['avg_ms']:.2f} ms | UADP: {u['avg_ms']:.2f} ms")

    return results


# =============================================================================
# PREFLIGHT: one message of each type for manual validation
# =============================================================================

def preflight(mqtt):
    """Sends 1 JSON + 1 UADP for tool validation before full benchmark."""
    from opcua_pubsub import NetworkMessage, DataSetMessage, DataValue
    from opcua_uadp import OPCUATypes

    print(f"\n{'=' * 55}")
    print("PRE-FLIGHT: 1 JSON + 1 UADP")
    print('=' * 55)

    # JSON
    nm = NetworkMessage("ESP32-Bench", "preflight-1")
    dm = DataSetMessage(1000, 1)
    dm.add_value("Val_F32_A", DataValue(25.5))
    dm.add_value("Val_I32_C", DataValue(42))
    nm.add_dataset_message(dm)
    json_payload = nm.to_json()
    mqtt.publish(TOPIC_JSON, json_payload)
    print(f"\n[JSON] -> {TOPIC_JSON} ({len(json_payload)} B)")
    print(f"  {json_payload}")

    time.sleep(0.5)

    # UADP
    fields = [
        ("Val_F32_A", 25.5, OPCUATypes.FLOAT),
        ("Val_I32_C", 42, OPCUATypes.INT32),
    ]
    uadp_payload = encode_uadp_interop("ESP32-Bench", 1000, fields)
    mqtt.publish(TOPIC_UADP, uadp_payload)
    print(f"\n[UADP] -> {TOPIC_UADP} ({len(uadp_payload)} B)")
    print(f"  Hex: {uadp_payload.hex()}")

    print(f"\n>>> Verify OpcCmd + MQTT Explorer/mosquitto_sub NOW <<<")


# =============================================================================
# FULL BENCHMARK
# =============================================================================

def run():
    """Full benchmark: size + memory + throughput + latency."""
    print("\n" + "#" * 55)
    print("#  OPC UA PubSub Benchmark: JSON vs UADP")
    print("#  UADP encoding: v7 (OpcCmd-validated, Jan 2026)")
    print("#" * 55)

    gc.collect()
    ram0 = gc.mem_free()
    print(f"\nInitial free RAM: {ram0 // 1024} KB ({ram0} B)")

    benchmark_size()
    benchmark_memory()

    mqtt = connect()
    if not mqtt:
        return

    preflight(mqtt)
    print("\nWaiting 5s - verify OpcCmd/MQTT Explorer...")
    time.sleep(5)

    r_tp = benchmark_throughput(mqtt, 50)
    gc.collect()

    print("\n" + "!" * 55)
    print("  Latency requires echo_server.py on PC!")
    print("!" * 55)

    r_lat = {}
    try:
        r_lat = benchmark_latency(mqtt, 30)
    except Exception as e:
        print(f"Latency error: {e}")

    mqtt.disconnect()
    gc.collect()

    ram1 = gc.mem_free()
    j = r_tp["json"]
    u = r_tp["uadp"]

    print("\n" + "#" * 55)
    print("#  FINAL REPORT")
    print("#" * 55)
    print(f"""
| Metric          | JSON             | UADP             |
|-----------------|------------------|------------------|
| Throughput      | {j['rate']:>7.1f} msg/s   | {u['rate']:>7.1f} msg/s   |
| Message size    | {j['bytes_per_msg']:>7} B       | {u['bytes_per_msg']:>7} B       |
| Wire ratio      |              1.0x | {j['bytes_per_msg']/u['bytes_per_msg']:>15.1f}x |""")

    jl = r_lat.get("json", {})
    ul = r_lat.get("uadp", {})
    if jl.get("avg_ms") and ul.get("avg_ms"):
        print(f"| Latency (RTT)   | {jl['avg_ms']:>7.2f} ms     | {ul['avg_ms']:>7.2f} ms     |")

    print(f"""
RAM: initial={ram0 // 1024} KB, final={ram1 // 1024} KB, delta={ram0 - ram1} B
Validation: check OpcCmd (UADP) + MQTT Explorer (JSON) logs.
""")
    print("[OK] Benchmark complete!")


# =============================================================================
# MENU
# =============================================================================

print("\nOPC UA PubSub Benchmark v2.1")
print("=" * 40)
print("  run()                   - Full benchmark")
print("  benchmark_size()        - Size only (offline)")
print("  benchmark_memory()      - Memory only (offline)")
print("  connect()               - WiFi+MQTT")
print("  preflight(mqtt)         - 1 msg each for validation")
print("  benchmark_throughput(mqtt, 50)")
print("  benchmark_latency(mqtt, 30)")