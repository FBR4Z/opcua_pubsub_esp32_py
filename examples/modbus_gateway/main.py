"""
ESP32 IT — Modbus RTU Client + Gateway OPC UA PubSub.

Fluxo: WiFi -> MQTT -> polling Modbus no OT (Server) -> publica via
opcua_pubsub.OPCUAPublisher (lib real do projeto).

Pré-requisitos no dispositivo (via Thonny):
- modbus_rtu_client.py, opcua_pubsub.py, config.py (copiado de config_example.py
  e preenchido com WiFi/MQTT reais) precisam estar na raiz do ESP32.
- umqtt.simple precisa estar instalado (não vem por padrão no firmware
  MicroPython stock). No Thonny: Tools > Manage packages > procurar
  "micropython-umqtt.simple" e instalar; ou via REPL:
  import mip; mip.install("umqtt.simple")
"""

import time
import network
from umqtt.simple import MQTTClient

from modbus_rtu_client import ModbusRTUClient
from opcua_pubsub import OPCUAPublisher

try:
    from config import (
        WIFI_SSID, WIFI_PASSWORD,
        MQTT_BROKER, MQTT_PORT, MQTT_USER, MQTT_PASSWORD,
        PUBLISHER_ID, DATASET_WRITER_ID, MQTT_TOPIC,
    )
except ImportError:
    raise RuntimeError(
        "config.py nao encontrado no dispositivo. Copie config_example.py "
        "para config.py e preencha WIFI_SSID/WIFI_PASSWORD/MQTT_BROKER."
    )

# ============================================================
# CONFIGURAÇÃO — Modbus
# ============================================================
SLAVE_ADDR = 1
POLL_INTERVAL_MS = 200   # intervalo de polling+publicação (independente do
                          # PUBLISH_INTERVAL em segundos usado noutros exemplos
                          # da lib, que era pensado pra demos mais lentas)

# Offsets — devem bater com HOLD_REG_* em modbus_params.h (lado OT)
REG_BASE_ANG      = 0
REG_OMBRO_ANG     = 1
REG_COTOVELO_ANG  = 2
REG_GARRA_ANG     = 3
REG_ESTEIRA_VEL   = 4
REG_ESTEIRA_STATE = 5
REG_SENSOR_DIST   = 6
REG_COUNT         = 7

# UART2 — cruzado com o OT (OT TX=17 -> IT RX=16, OT RX=16 <- IT TX=17)
modbus = ModbusRTUClient(uart_id=2, tx=17, rx=16, baudrate=115200, timeout_ms=200)


def wifi_connect(ssid, password, timeout_ms=15000):
    sta = network.WLAN(network.STA_IF)
    sta.active(True)
    if not sta.isconnected():
        print("[wifi] conectando a", ssid)
        sta.connect(ssid, password)
        t0 = time.ticks_ms()
        while not sta.isconnected():
            if time.ticks_diff(time.ticks_ms(), t0) > timeout_ms:
                raise RuntimeError("Timeout conectando ao WiFi")
            time.sleep_ms(200)
    print("[wifi] conectado, IP =", sta.ifconfig()[0])
    return sta


def poll_once():
    regs = modbus.read_holding_registers(SLAVE_ADDR, 0, REG_COUNT)
    if regs is None:
        print("[modbus] timeout ou erro na leitura")
        return None

    return {
        "base_ang": regs[REG_BASE_ANG],
        "ombro_ang": regs[REG_OMBRO_ANG],
        "cotovelo_ang": regs[REG_COTOVELO_ANG],
        "garra_ang": regs[REG_GARRA_ANG],
        "esteira_vel": regs[REG_ESTEIRA_VEL],
        "esteira_state": regs[REG_ESTEIRA_STATE],
        "sensor_dist": regs[REG_SENSOR_DIST],
    }


def main():
    wifi_connect(WIFI_SSID, WIFI_PASSWORD)

    mqtt_client = MQTTClient(
        "esp32-it-modbus-gateway", MQTT_BROKER, port=MQTT_PORT,
        user=MQTT_USER, password=MQTT_PASSWORD,
    )
    publisher = OPCUAPublisher(PUBLISHER_ID, mqtt_client, base_topic=MQTT_TOPIC)

    if not publisher.connect():
        raise RuntimeError("Falha ao conectar no broker MQTT (" + str(MQTT_BROKER) + ")")

    print("[IT] Loop iniciado. Publisher ID =", PUBLISHER_ID, "Topic =", MQTT_TOPIC)
    while True:
        values = poll_once()
        if values is not None:
            publisher.publish(DATASET_WRITER_ID, values)
        time.sleep_ms(POLL_INTERVAL_MS)


if __name__ == "__main__":
    main()