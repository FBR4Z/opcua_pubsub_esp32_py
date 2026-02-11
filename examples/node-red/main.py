"""
OPC UA PubSub + Node-RED Bidirectional Example
ESP32 MicroPython — Minimal "1-bit each way" demo

Hardware:
  - Push button on GPIO4 (pulled up internally, connects to GND)
  - LED on GPIO2 (built-in LED on most ESP32 boards)

Communication:
  ESP32 → Node-RED:  Button state via OPC UA PubSub JSON
  Node-RED → ESP32:  LED command via OPC UA PubSub JSON

Topics:
  opcua/json/nodered/button   (ESP32 publishes)
  opcua/json/nodered/led/cmd  (ESP32 subscribes)

Author: Fábio Braz — Master's Thesis, UEA
License: MIT
"""

import gc
import time
import ujson
import machine
import network
from umqtt.simple import MQTTClient

# --- Library imports ---
# Uses opcua_pubsub.py from src/ (copy to ESP32 root)
from opcua_pubsub import (
    NetworkMessage, DataSetMessage, DataValue,
    parse_network_message
)

# --- Configuration ---
try:
    from config import (
        WIFI_SSID, WIFI_PASSWORD,
        MQTT_BROKER, MQTT_PORT,
        PUBLISHER_ID
    )
except ImportError:
    print("ERROR: config.py not found!")
    print("Copy config_example.py to config.py and edit.")
    raise SystemExit

# --- Constants ---
TOPIC_BUTTON = "opcua/json/nodered/button"
TOPIC_LED_CMD = "opcua/json/nodered/led/cmd"
DATASET_WRITER_BUTTON = 1001
BUTTON_PIN = 4   # GPIO4 — push button to GND
LED_PIN = 2      # GPIO2 — built-in LED (most ESP32 boards)
PUBLISH_INTERVAL_MS = 200  # Check button every 200ms


# =============================================================================
# Hardware Setup
# =============================================================================

def setup_hardware():
    """Initialize button (input pull-up) and LED (output)."""
    button = machine.Pin(BUTTON_PIN, machine.Pin.IN, machine.Pin.PULL_UP)
    led = machine.Pin(LED_PIN, machine.Pin.OUT)
    led.value(0)  # Start with LED off
    print(f"[HW] Button: GPIO{BUTTON_PIN} | LED: GPIO{LED_PIN}")
    return button, led


# =============================================================================
# WiFi
# =============================================================================

def connect_wifi():
    """Connect to WiFi, return True if successful."""
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    time.sleep(1)

    if wlan.isconnected():
        print(f"[WiFi] Already connected: {wlan.ifconfig()[0]}")
        return True

    print(f"[WiFi] Connecting to {WIFI_SSID}...", end="")
    wlan.connect(WIFI_SSID, WIFI_PASSWORD)

    for _ in range(20):
        if wlan.isconnected():
            print(f"\n[WiFi] OK! IP: {wlan.ifconfig()[0]}")
            return True
        print(".", end="")
        time.sleep(1)

    print("\n[WiFi] FAILED!")
    return False


# =============================================================================
# MQTT Subscriber Callback
# =============================================================================

def make_led_callback(led):
    """
    Creates MQTT callback that parses OPC UA PubSub JSON
    and controls the LED.

    Expected message from Node-RED:
    {
      "MessageType": "ua-data",
      "PublisherId": "NodeRED-Dashboard",
      "Messages": [{
        "Payload": {
          "LED": {"Value": true, "SourceTimestamp": "..."}
        }
      }]
    }
    """
    def on_message(topic, msg):
        try:
            topic_str = topic.decode() if isinstance(topic, bytes) else topic
            payload = parse_network_message(msg)

            if payload is None:
                print(f"[SUB] Ignored non-OPC UA message on {topic_str}")
                return

            # Extract LED value from OPC UA Payload
            led_field = payload.get("LED", {})
            if isinstance(led_field, dict):
                led_value = led_field.get("Value", False)
            else:
                led_value = bool(led_field)

            led.value(1 if led_value else 0)
            state = "ON" if led_value else "OFF"
            print(f"[SUB] LED -> {state}")

        except Exception as e:
            print(f"[SUB] Error: {e}")

    return on_message


# =============================================================================
# OPC UA Publisher Helper
# =============================================================================

def publish_button_state(mqtt, publisher_id, seq, button_pressed):
    """
    Publishes button state as OPC UA PubSub JSON NetworkMessage.

    Uses the library classes: NetworkMessage, DataSetMessage, DataValue.
    """
    nm = NetworkMessage(
        publisher_id=publisher_id,
        message_id=str(seq)
    )

    dm = DataSetMessage(
        dataset_writer_id=DATASET_WRITER_BUTTON,
        sequence_number=seq
    )
    dm.add_value("Button", DataValue(button_pressed))

    nm.add_dataset_message(dm)
    json_str = nm.to_json()

    mqtt.publish(TOPIC_BUTTON, json_str)
    return len(json_str)


# =============================================================================
# Main
# =============================================================================

def main():
    print("\n" + "=" * 50)
    print("OPC UA PubSub + Node-RED Example")
    print("Button (GPIO4) -> Node-RED Dashboard")
    print("Node-RED Dashboard -> LED (GPIO2)")
    print("=" * 50)

    gc.collect()
    print(f"[RAM] Free: {gc.mem_free() // 1024} KB")

    # 1. Hardware
    button, led = setup_hardware()

    # 2. WiFi
    if not connect_wifi():
        return

    # 3. MQTT
    print(f"[MQTT] Connecting to {MQTT_BROKER}:{MQTT_PORT}...", end="")
    mqtt = MQTTClient(PUBLISHER_ID, MQTT_BROKER, MQTT_PORT)
    mqtt.set_callback(make_led_callback(led))

    try:
        mqtt.connect()
        print(" OK")
    except OSError as e:
        print(f" FAILED: {e}")
        return

    # Subscribe to LED commands from Node-RED
    mqtt.subscribe(TOPIC_LED_CMD)
    print(f"[MQTT] Subscribed to: {TOPIC_LED_CMD}")
    print(f"[MQTT] Publishing to: {TOPIC_BUTTON}")

    # 4. Main loop
    seq = 0
    prev_button = None  # Track state changes

    print("\n[READY] Press button or toggle LED from Node-RED dashboard")
    print("        Press Ctrl+C to stop\n")

    try:
        while True:
            # Check for incoming LED commands (non-blocking)
            mqtt.check_msg()

            # Read button (active LOW with pull-up)
            button_pressed = not button.value()

            # Only publish on state change (edge detection)
            if button_pressed != prev_button:
                prev_button = button_pressed
                seq += 1

                msg_len = publish_button_state(
                    mqtt, PUBLISHER_ID, seq, button_pressed
                )

                state = "PRESSED" if button_pressed else "RELEASED"
                print(f"[PUB] #{seq} Button {state} ({msg_len} B)")

            time.sleep_ms(PUBLISH_INTERVAL_MS)

    except KeyboardInterrupt:
        print("\n[STOP] Interrupted by user")
    finally:
        led.value(0)
        mqtt.disconnect()
        print("[DONE] Disconnected")


if __name__ == "__main__":
    main()