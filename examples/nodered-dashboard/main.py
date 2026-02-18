"""
OPC UA PubSub + Node-RED Full Dashboard Example
ESP32 MicroPython — Sensors + Actuators bidirectional demo

Hardware:
  - Push button on GPIO4 (pull-up, connects to GND)
  - LED on GPIO15 (with 220Ω resistor to GND)
  - DHT11 on GPIO13 (3-pin module with built-in pull-up)
  - Servo SG90 on GPIO18 (signal pin, 5V from VIN)
  - Potentiometer on GPIO34 (ADC1, 0-3.3V)

Communication:
  ESP32 → Node-RED:
    - opcua/json/nodered/button   (on state change)
    - opcua/json/nodered/sensors  (periodic: temp, humid, pot, servo)

  Node-RED → ESP32:
    - opcua/json/nodered/cmd      (LED on/off, servo angle 0-180)

Author: Fábio Braz — Master's Thesis, UEA
License: MIT
"""

import gc
import time
import dht
import machine
import network
import ujson
from umqtt.simple import MQTTClient

from opcua_pubsub import (
    NetworkMessage, DataSetMessage, DataValue,
    parse_network_message
)

# --- Configuration ---
try:
    from config import (
        WIFI_SSID, WIFI_PASSWORD,
        MQTT_BROKER, MQTT_PORT,
        PUBLISHER_ID,
        PIN_BUTTON, PIN_LED, PIN_DHT, PIN_SERVO, PIN_POT,
        SENSOR_INTERVAL_MS
    )
except ImportError:
    print("ERROR: config.py not found!")
    print("Copy config_example.py to config.py and edit.")
    raise SystemExit

# --- Constants ---
TOPIC_BUTTON  = "opcua/json/nodered/button"
TOPIC_SENSORS = "opcua/json/nodered/sensors"
TOPIC_CMD     = "opcua/json/nodered/cmd"

DSW_BUTTON  = 1001  # DataSetWriter IDs
DSW_SENSORS = 1002


# =============================================================================
# Hardware
# =============================================================================

class Hardware:
    """Manages all hardware peripherals."""

    def __init__(self):
        # Button (active LOW with internal pull-up)
        self.button = machine.Pin(PIN_BUTTON, machine.Pin.IN, machine.Pin.PULL_UP)

        # LED (active HIGH)
        self.led = machine.Pin(PIN_LED, machine.Pin.OUT)
        self.led.value(0)

        # DHT11 sensor
        self.dht = dht.DHT11(machine.Pin(PIN_DHT))
        self.last_temp = 0.0
        self.last_humid = 0.0

        # Potentiometer (ADC)
        self.pot = machine.ADC(machine.Pin(PIN_POT))
        self.pot.atten(machine.ADC.ATTN_11DB)   # 0-3.3V range
        self.pot.width(machine.ADC.WIDTH_12BIT)  # 0-4095

        # Servo (PWM at 50 Hz)
        self.servo_pwm = machine.PWM(machine.Pin(PIN_SERVO), freq=50)
        self.servo_angle = 90
        self._set_servo(90)

        print(f"[HW] Button:GPIO{PIN_BUTTON} LED:GPIO{PIN_LED} "
              f"DHT:GPIO{PIN_DHT} Servo:GPIO{PIN_SERVO} Pot:GPIO{PIN_POT}")

    # --- Servo helpers ---
    def _angle_to_duty(self, angle):
        """Convert angle (0-180) to PWM duty (0-1023).
        SG90: 0.5ms (0°) to 2.5ms (180°) at 50Hz (20ms period)."""
        angle = max(0, min(180, angle))
        pulse_ms = 0.5 + (angle / 180.0) * 2.0  # 0.5ms to 2.5ms
        duty = int(pulse_ms / 20.0 * 1023)
        return duty

    def _set_servo(self, angle):
        """Set servo position."""
        self.servo_angle = max(0, min(180, angle))
        self.servo_pwm.duty(self._angle_to_duty(self.servo_angle))

    def set_servo(self, angle):
        """Public method to set servo angle."""
        self._set_servo(angle)
        print(f"[HW] Servo -> {self.servo_angle}°")

    def set_led(self, state):
        """Set LED state."""
        self.led.value(1 if state else 0)
        print(f"[HW] LED -> {'ON' if state else 'OFF'}")

    def read_button(self):
        """Read button (True = pressed, active LOW)."""
        return not self.button.value()

    def read_dht(self):
        """Read DHT11. Returns (temp, humid) or cached values on error."""
        try:
            self.dht.measure()
            self.last_temp = self.dht.temperature()
            self.last_humid = self.dht.humidity()
        except OSError as e:
            print(f"[DHT] Read error: {e}")
        return self.last_temp, self.last_humid

    def read_pot_percent(self):
        """Read potentiometer as 0-100%."""
        raw = self.pot.read()
        return round(raw / 4095.0 * 100.0, 1)

    def cleanup(self):
        """Release resources."""
        self.led.value(0)
        self.servo_pwm.deinit()


# =============================================================================
# WiFi
# =============================================================================

def connect_wifi():
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
# MQTT Subscriber — Command Handler
# =============================================================================

def make_cmd_callback(hw):
    """
    Parses OPC UA PubSub JSON commands from Node-RED.

    Expected payload fields:
      "LED":   {"Value": true/false}
      "Servo": {"Value": 0-180}
    """
    def on_message(topic, msg):
        try:
            payload = parse_network_message(msg)
            if payload is None:
                return

            # LED command
            led_field = payload.get("LED")
            if led_field is not None:
                val = led_field.get("Value") if isinstance(led_field, dict) else led_field
                hw.set_led(bool(val))

            # Servo command
            servo_field = payload.get("Servo")
            if servo_field is not None:
                val = servo_field.get("Value") if isinstance(servo_field, dict) else servo_field
                hw.set_servo(int(val))

        except Exception as e:
            print(f"[CMD] Error: {e}")

    return on_message


# =============================================================================
# OPC UA Publishers
# =============================================================================

def publish_button(mqtt, seq, pressed):
    """Publish button state as OPC UA PubSub JSON."""
    nm = NetworkMessage(publisher_id=PUBLISHER_ID, message_id=str(seq))
    dm = DataSetMessage(dataset_writer_id=DSW_BUTTON, sequence_number=seq)
    dm.add_value("Button", DataValue(pressed))
    nm.add_dataset_message(dm)

    json_str = nm.to_json()
    mqtt.publish(TOPIC_BUTTON, json_str)
    return len(json_str)


def publish_sensors(mqtt, seq, temp, humid, pot_pct, servo_angle):
    """Publish all sensor readings as OPC UA PubSub JSON."""
    nm = NetworkMessage(publisher_id=PUBLISHER_ID, message_id=str(seq))
    dm = DataSetMessage(dataset_writer_id=DSW_SENSORS, sequence_number=seq)

    dm.add_value("Temperature", DataValue(temp))
    dm.add_value("Humidity", DataValue(humid))
    dm.add_value("Potentiometer", DataValue(pot_pct))
    dm.add_value("ServoPosition", DataValue(servo_angle))

    nm.add_dataset_message(dm)
    json_str = nm.to_json()
    mqtt.publish(TOPIC_SENSORS, json_str)
    return len(json_str)


# =============================================================================
# Main
# =============================================================================

def main():
    print("\n" + "=" * 55)
    print("  OPC UA PubSub + Node-RED — Full Dashboard Demo")
    print("  Button | DHT11 | Pot | LED | Servo")
    print("=" * 55)

    gc.collect()
    print(f"[RAM] Free: {gc.mem_free() // 1024} KB")

    # 1. Hardware
    hw = Hardware()

    # 2. WiFi
    if not connect_wifi():
        return

    # 3. MQTT
    print(f"[MQTT] Connecting to {MQTT_BROKER}:{MQTT_PORT}...", end="")
    mqtt = MQTTClient(PUBLISHER_ID, MQTT_BROKER, MQTT_PORT)
    mqtt.set_callback(make_cmd_callback(hw))

    try:
        mqtt.connect()
        print(" OK")
    except OSError as e:
        print(f" FAILED: {e}")
        return

    mqtt.subscribe(TOPIC_CMD)
    print(f"[MQTT] Sub: {TOPIC_CMD}")
    print(f"[MQTT] Pub: {TOPIC_BUTTON}, {TOPIC_SENSORS}")

    # 4. Main loop
    seq = 0
    prev_button = None
    last_sensor_time = 0

    print("\n[READY] Dashboard: http://<your-pc-ip>:1880/dashboard")
    print("        Ctrl+C to stop\n")

    try:
        while True:
            # Check incoming commands (non-blocking)
            mqtt.check_msg()

            now = time.ticks_ms()

            # --- Button: publish on change ---
            btn = hw.read_button()
            if btn != prev_button:
                prev_button = btn
                seq += 1
                n = publish_button(mqtt, seq, btn)
                state = "PRESSED" if btn else "RELEASED"
                print(f"[BTN] #{seq} {state} ({n} B)")

            # --- Sensors: publish periodically ---
            if time.ticks_diff(now, last_sensor_time) >= SENSOR_INTERVAL_MS:
                last_sensor_time = now
                seq += 1

                temp, humid = hw.read_dht()
                pot = hw.read_pot_percent()

                n = publish_sensors(mqtt, seq, temp, humid, pot, hw.servo_angle)
                print(f"[SNS] #{seq} T={temp}°C H={humid}% "
                      f"Pot={pot}% Servo={hw.servo_angle}° ({n} B)")

                gc.collect()

            time.sleep_ms(100)

    except KeyboardInterrupt:
        print("\n[STOP] Interrupted")
    finally:
        hw.cleanup()
        mqtt.disconnect()
        print("[DONE] Disconnected")


if __name__ == "__main__":
    main()