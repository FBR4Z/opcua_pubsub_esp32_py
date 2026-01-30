"""
OPC UA PubSub LCD Example - Configuration Template
Copy this file to config.py and edit with your settings.

Exemplo de LCD com OPC UA PubSub - Template de Configuração
Copie este arquivo para config.py e edite com suas configurações.
"""

# =============================================================================
# WiFi Configuration / Configuração WiFi
# =============================================================================

WIFI_SSID = "YOUR_WIFI_SSID"          # Your WiFi network name
WIFI_PASSWORD = "YOUR_WIFI_PASSWORD"   # Your WiFi password

# =============================================================================
# MQTT Configuration / Configuração MQTT
# =============================================================================

# MQTT Broker IP address or hostname
# Public brokers for testing (no authentication):
#   - broker.hivemq.com (port 1883)
#   - test.mosquitto.org (port 1883)
#   - broker.emqx.io (port 1883)
# Local broker example: "192.168.1.100"

MQTT_BROKER = "YOUR_BROKER_IP"
MQTT_PORT = 1883

# Credentials (set to None if not using authentication)
MQTT_USER = None
MQTT_PASSWORD = None

# =============================================================================
# OPC UA PubSub Configuration / Configuração OPC UA PubSub
# =============================================================================

# Unique publisher identifier
# Suggestion: use a prefix + MAC address or serial number
PUBLISHER_ID = "ESP32-OPCUA-LCD-001"

# DataSetWriter ID - identifies the data set
DATASET_WRITER_ID = 1000

# Base MQTT topic
# Recommended format: opcua/data/{publisher_id}
MQTT_TOPIC = "opcua/lcd/data"
MQTT_TOPIC_METADATA = "opcua/lcd/metadata"

# =============================================================================
# LCD Configuration / Configuração LCD
# =============================================================================

# I2C pins for ESP32
I2C_SCL_PIN = 22  # GPIO22 - Clock
I2C_SDA_PIN = 21  # GPIO21 - Data

# Common I2C addresses for PCF8574 LCD modules
# 0x27 is most common, alternatives: 0x3F, 0x20, 0x38
LCD_I2C_ADDR = 0x27

# =============================================================================
# Publishing Configuration / Configuração de Publicação
# =============================================================================

# Publish interval in seconds
PUBLISH_INTERVAL = 3

# =============================================================================
# Debug Configuration / Configuração de Debug
# =============================================================================

DEBUG = True
