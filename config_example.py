"""
OPC UA PubSub ESP32 - Configuration Template
Copy this file to config.py and edit with your settings.

Copie este arquivo para config.py e edite com suas configurações.
"""

# =============================================================================
# WiFi Configuration
# =============================================================================

WIFI_SSID = "YOUR_WIFI_SSID"
WIFI_PASSWORD = "YOUR_WIFI_PASSWORD"

# =============================================================================
# MQTT Broker Configuration
# =============================================================================

# Local broker example: "192.168.1.100"
# Public brokers for testing:
#   - broker.hivemq.com
#   - test.mosquitto.org
#   - broker.emqx.io

MQTT_BROKER = "YOUR_BROKER_IP"
MQTT_PORT = 1883

# Authentication (set to None if not required)
MQTT_USER = None
MQTT_PASSWORD = None

# =============================================================================
# OPC UA PubSub Configuration
# =============================================================================

# Unique publisher identifier (URN format recommended)
PUBLISHER_ID = "ESP32-OPCUA-001"

# DataSetWriter ID
DATASET_WRITER_ID = 1000

# MQTT topic for data publication
MQTT_TOPIC = "opcua/data/esp32"

# =============================================================================
# Publishing Configuration
# =============================================================================

# Interval between publications (seconds)
PUBLISH_INTERVAL = 5

# =============================================================================
# Debug Configuration
# =============================================================================

DEBUG = True
