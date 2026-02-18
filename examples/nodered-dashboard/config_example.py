"""
OPC UA PubSub + Node-RED Full Dashboard — Configuration Template
Copy this file to config.py and edit with your settings.
"""

# =============================================================================
# WiFi
# =============================================================================

WIFI_SSID = "YOUR_WIFI_SSID"
WIFI_PASSWORD = "YOUR_WIFI_PASSWORD"

# =============================================================================
# MQTT Broker (PC running Mosquitto + Node-RED)
# =============================================================================

MQTT_BROKER = "192.168.0.XX"
MQTT_PORT = 1883

# =============================================================================
# OPC UA PubSub
# =============================================================================

PUBLISHER_ID = "ESP32-NodeRED-001"

# =============================================================================
# Hardware Pins
# =============================================================================

PIN_BUTTON = 4    # Push button (pull-up, connects to GND)
PIN_LED    = 15   # External LED (with 220Ω resistor to GND)
PIN_DHT    = 13   # DHT11 data pin (3-pin module)
PIN_SERVO  = 18   # Servo SG90 signal (PWM)
PIN_POT    = 34   # Potentiometer wiper (ADC1, input-only)

# =============================================================================
# Timing
# =============================================================================

SENSOR_INTERVAL_MS = 2000  # Publish sensors every 2 seconds