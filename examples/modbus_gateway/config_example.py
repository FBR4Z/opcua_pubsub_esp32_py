"""
Configuração do gateway IT (Modbus RTU Client -> OPC UA PubSub).
Copie este arquivo para config.py e preencha com seus dados reais.
config.py NÃO deve ser commitado (tem credenciais).
"""

# ============================================================
# WiFi
# ============================================================
WIFI_SSID = "OPC_UA"              # roteador da célula
WIFI_PASSWORD = "SUA_SENHA"

# ============================================================
# MQTT Broker
# ============================================================
# RPi 5 da célula (Mosquitto + AAS + Node-RED), IP fixo — ver deploy/rpi5/README.md
MQTT_BROKER = "192.168.0.2"
NTP_HOST = "192.168.0.2"           # chrony do RPi
MQTT_PORT = 1883
MQTT_USER = None
MQTT_PASSWORD = None

# ============================================================
# OPC UA PubSub
# ============================================================
PUBLISHER_ID = "urn:uea:celula-robotica:esp32-it"
DATASET_WRITER_ID = 2000          # o AAS registra este valor em OPCUAPubSubInfo
MQTT_TOPIC = "it/opcua/celula_robotica"   # assinado pelo aas_gateway e pelo Node-RED