"""
Echo Server for OPC UA PubSub Benchmark
Runs on PC (Python 3 + paho-mqtt)

Listens to ping topics and echoes immediately for RTT measurement.

Topics:
  opcua/json/ping  ->  opcua/json/echo
  opcua/uadp/ping  ->  opcua/uadp/echo

Usage:
    python echo_server.py                # broker on localhost
    python echo_server.py 192.168.0.27   # broker on specific IP

Author: Fabio
Project: Master's Thesis - UEA
"""

import time
import sys

try:
    import paho.mqtt.client as mqtt
except ImportError:
    print("ERROR: paho-mqtt not installed")
    print("Run:   pip install paho-mqtt")
    sys.exit(1)

BROKER = sys.argv[1] if len(sys.argv) > 1 else "localhost"
PORT = 1883

ECHO_MAP = {
    "opcua/json/ping": "opcua/json/echo",
    "opcua/uadp/ping": "opcua/uadp/echo",
}

stats = {"received": 0, "echoed": 0, "errors": 0}


def on_connect(client, userdata, flags, rc, properties=None):
    if rc == 0:
        print(f"[Echo] Connected to {BROKER}:{PORT}")
        for topic, echo_topic in ECHO_MAP.items():
            client.subscribe(topic)
            print(f"[Echo] {topic} -> {echo_topic}")
        print("-" * 55)
        print("Waiting for ESP32 messages... (Ctrl+C to stop)")
    else:
        print(f"[Echo] Connection failed: rc={rc}")


def on_message(client, userdata, msg):
    stats["received"] += 1
    echo_topic = ECHO_MAP.get(msg.topic)
    if echo_topic:
        try:
            client.publish(echo_topic, msg.payload)
            stats["echoed"] += 1
            if stats["echoed"] % 10 == 0:
                print(f"[Echo] {stats['echoed']} messages echoed "
                      f"(JSON: {msg.topic.startswith('opcua/json')})")
        except Exception as e:
            stats["errors"] += 1
            print(f"[Error] {e}")


def main():
    print("=" * 55)
    print("OPC UA PubSub - Latency Echo Server")
    print("=" * 55)
    print(f"Broker: {BROKER}:{PORT}")
    print("-" * 55)

    client = mqtt.Client(
        mqtt.CallbackAPIVersion.VERSION2,
        client_id="Echo-Bench-Server"
    )
    client.on_connect = on_connect
    client.on_message = on_message

    try:
        client.connect(BROKER, PORT, 60)
        client.loop_forever()
    except KeyboardInterrupt:
        print("\n[Echo] Interrupted by user")
    except Exception as e:
        print(f"[Error] {e}")
    finally:
        print(f"\nFinal stats: received={stats['received']}, "
              f"echoed={stats['echoed']}, errors={stats['errors']}")
        client.disconnect()


if __name__ == "__main__":
    main()