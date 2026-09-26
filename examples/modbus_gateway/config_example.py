"""
Configuração do gateway IT (Modbus RTU Client -> OPC UA PubSub).
Copie este arquivo para config.py e preencha com seus dados reais.
config.py NÃO deve ser commitado (tem credenciais).
"""

# ============================================================
# WiFi
# ============================================================
WIFI_SSID = "SUA_REDE"
WIFI_PASSWORD = "SUA_SENHA"

# ============================================================
# MQTT Broker
# ============================================================
# Broker local exemplo: "192.168.0.XX" (o mesmo usado no aas_gateway.py)
MQTT_BROKER = "192.168.0.XX"
MQTT_PORT = 1883
MQTT_USER = None
MQTT_PASSWORD = None

# ============================================================
# OPC UA PubSub
# ============================================================
PUBLISHER_ID = "urn:esp32:it:modbus-gateway"
DATASET_WRITER_ID = 2000          # diferente do usado nos outros exemplos (ex: LCD=1000)
MQTT_TOPIC = "opcua/data/celula_robotica"