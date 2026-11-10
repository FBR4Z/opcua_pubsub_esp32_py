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
from machine import I2C, Pin
from umqtt.simple import MQTTClient

from lcd_i2c_test import LCD_I2C
from modbus_rtu_client import ModbusRTUClient
from opcua_pubsub import OPCUAPublisher, DataValue, StatusCode

try:
    from config import (
        WIFI_SSID, WIFI_PASSWORD,
        MQTT_BROKER, MQTT_PORT, MQTT_USER, MQTT_PASSWORD,
        PUBLISHER_ID, DATASET_WRITER_ID, MQTT_TOPIC,
    )
    try:
        from config import NTP_HOST
    except ImportError:
        NTP_HOST = MQTT_BROKER   # o RPi da célula é broker e servidor de hora
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
RECONNECT_MS = 3000

# Offsets — devem bater com HOLD_REG_* em modbus_params.h (lado OT)
REG_BASE_ANG      = 0
REG_OMBRO_ANG     = 1
REG_COTOVELO_ANG  = 2
REG_GARRA_ANG     = 3
REG_ESTEIRA_VEL   = 4
REG_ESTEIRA_STATE = 5
REG_SENSOR_DIST   = 6
REG_CYCLE_COUNT   = 7
REG_AUTO_FASE     = 8
REG_COUNT         = 9

SENSOR_SEM_LEITURA = 0xFFFF
PECA_LIMIAR_CM     = 8   # mesmo LIMIAR_PADRAO_CM do auto_cycle.c (OT)

# UART2 — cruzado com o OT (OT TX=17 -> IT RX=16, OT RX=16 <- IT TX=17)
modbus = ModbusRTUClient(uart_id=2, tx=17, rx=16, baudrate=115200, timeout_ms=200)

# ============================================================
# LCD I2C (PCF8574) — mesmos pinos do lcd_i2c_test.py
# ============================================================
LCD_SDA = 21
LCD_SCL = 22
# "á" não existe na ROM do HD44780: desenhado no caractere 0 da CGRAM
A_AGUDO = [0x02, 0x04, 0x0E, 0x01, 0x0F, 0x11, 0x0F, 0x00]


def lcd_saudacao():
    """Mostra "Oi Fábio" no LCD. Sem LCD, o gateway segue normalmente."""
    try:
        i2c = I2C(0, scl=Pin(LCD_SCL), sda=Pin(LCD_SDA), freq=400000)
        devices = i2c.scan()
        if not devices:
            print("[lcd] nenhum dispositivo I2C")
            return None
        lcd = LCD_I2C(i2c, addr=devices[0])
        lcd.create_char(0, A_AGUDO)
        lcd.clear()
        lcd.set_cursor(4, 0)
        lcd.write("Oi F")
        lcd.write_char(0)
        lcd.write("bio")
        print("[lcd] Oi Fabio")
        return lcd
    except Exception as e:
        print("[lcd] erro:", e)
        return None


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


def ntp_sync(host):
    """Acerta o RTC (UTC) pelo chrony do RPi, para o SourceTimestamp sair certo."""
    try:
        import ntptime
        ntptime.host = host
        ntptime.settime()
        print("[ntp] hora acertada por", host, time.gmtime())
        return True
    except Exception as e:
        print("[ntp] falhou (", host, "):", e)
        return False


def poll_once():
    """Lê o OT e monta o DataSet com os campos da Tabela tab:modbus_registers
    da dissertação (os mesmos que o AAS e o Node-RED consomem)."""
    regs = modbus.read_holding_registers(SLAVE_ADDR, 0, REG_COUNT)
    if regs is None:
        print("[modbus] timeout ou erro na leitura")
        return None

    dist = regs[REG_SENSOR_DIST]
    if dist == SENSOR_SEM_LEITURA:
        sensor = DataValue(None, StatusCode.BAD_SENSOR_FAILURE)
        peca = DataValue(False, StatusCode.UNCERTAIN)
    else:
        sensor = dist
        peca = dist < PECA_LIMIAR_CM

    return {
        "JointBase": float(regs[REG_BASE_ANG]),          # graus
        "JointShoulder": float(regs[REG_OMBRO_ANG]),
        "JointElbow": float(regs[REG_COTOVELO_ANG]),
        "JointGripper": float(regs[REG_GARRA_ANG]),
        "ConveyorSpeed": regs[REG_ESTEIRA_VEL],          # %
        "ConveyorRunning": regs[REG_ESTEIRA_STATE] != 0,
        "SensorDistance": sensor,                        # cm
        "PieceDetected": peca,
        "CycleCount": regs[REG_CYCLE_COUNT],
        "AutoPhase": regs[REG_AUTO_FASE],                # auto_fase_t do OT
    }


def main():
    lcd_saudacao()
    # O roteador da célula também demora a ligar: insiste no Wi-Fi
    while True:
        try:
            wifi_connect(WIFI_SSID, WIFI_PASSWORD)
            break
        except RuntimeError as e:
            print("[wifi]", e, "- nova tentativa")
    ntp_ok = ntp_sync(NTP_HOST)

    mqtt_client = MQTTClient(
        "esp32-it-modbus-gateway", MQTT_BROKER, port=MQTT_PORT,
        user=MQTT_USER, password=MQTT_PASSWORD,
    )
    publisher = OPCUAPublisher(PUBLISHER_ID, mqtt_client, base_topic=MQTT_TOPIC)

    # O ESP32 liga bem antes do RPi (broker): tenta até conseguir
    while not publisher.connect():
        print("[IT] broker", MQTT_BROKER, "indisponivel, nova tentativa em", RECONNECT_MS, "ms")
        time.sleep_ms(RECONNECT_MS)
    if not ntp_ok:
        ntp_ok = ntp_sync(NTP_HOST)

    print("[IT] Loop iniciado. Publisher ID =", PUBLISHER_ID, "Topic =", MQTT_TOPIC)
    while True:
        values = poll_once()
        if values is not None and not publisher.publish(DATASET_WRITER_ID, values):
            # Broker caiu (ex.: RPi reiniciado): reconecta sem parar o polling
            publisher.disconnect()
            time.sleep_ms(RECONNECT_MS)
            if publisher.connect() and not ntp_ok:
                ntp_ok = ntp_sync(NTP_HOST)
        time.sleep_ms(POLL_INTERVAL_MS)


if __name__ == "__main__":
    main()