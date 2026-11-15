"""
ESP32 IT — Modbus RTU Client + Gateway OPC UA PubSub.

Fluxo: WiFi -> NTP -> MQTT -> polling Modbus no OT (Server) -> publica via
opcua_pubsub.OPCUAPublisher (lib real do projeto).

Pré-requisitos no dispositivo (via Thonny):
- modbus_rtu_client.py, opcua_pubsub.py, lcd_i2c_test.py, nokia5110.py,
  painel.py e config.py (copiado de config_example.py e preenchido com
  WiFi/MQTT reais) precisam estar na raiz do ESP32.
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
from nokia5110 import Nokia5110
import painel

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
# Vigia da conexão MQTT: com QoS 0 uma conexão TCP "meio morta" (ex.: o RPi saiu da
# rede e voltou) não dá erro na publicação; só o PINGRESP do broker prova que ela vive.
PING_MS = 5000           # PINGREQ a cada 5 s
PING_TIMEOUT_MS = 12000  # sem PINGRESP há 12 s -> reconecta
SOCK_TIMEOUT_S = 2       # escrita travada vira erro em vez de parar o laço
MQTT_KEEPALIVE_S = 30    # o broker descarta a conexão antiga depois de 1,5 x isto
# O RPi não tem bateria no RTC: logo depois do boot ele serve a hora do último
# desligamento até o chrony acertar pelo PC (~20 s). NTP periódico corrige sozinho.
NTP_RESYNC_MS = 60000

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


def nokia_init():
    """Inicia o Nokia 5110. Sem display, o gateway segue normalmente."""
    try:
        d = Nokia5110()
        painel.nokia_boot(d, "iniciando")
        print("[nokia] ok")
        return d
    except Exception as e:
        print("[nokia] erro:", e)
        return None


def mostra(lcd, nokia, l0, l1, nk):
    """Mensagem de boot nos dois displays (erros de display nunca param o gateway)."""
    try:
        if lcd:
            lcd.print_line(0, l0)
            lcd.print_line(1, l1)
        if nokia:
            painel.nokia_boot(nokia, nk)
    except Exception as e:
        print("[display] erro:", e)


def wifi_connect(ssid, password, timeout_ms=15000):
    sta = network.WLAN(network.STA_IF)
    sta.active(True)
    # A conexão sobrevive ao soft reset: pode ter ficado em outra rede
    if sta.isconnected() and sta.config("ssid") != ssid:
        print("[wifi] saindo de", sta.config("ssid"))
        sta.disconnect()
        while sta.isconnected():
            time.sleep_ms(100)
    if not sta.isconnected():
        print("[wifi] conectando a", ssid)
        # Sem a rede, o ESP32 segue tentando sozinho; connect() por cima dessa
        # tentativa pendente dá "OSError: Wifi Internal State Error"
        sta.disconnect()
        sta.connect(ssid, password)
        t0 = time.ticks_ms()
        while not sta.isconnected():
            if time.ticks_diff(time.ticks_ms(), t0) > timeout_ms:
                sta.disconnect()
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


def mqtt_conectar(publisher):
    if not publisher.connect():
        return False
    publisher.mqtt.sock.settimeout(SOCK_TIMEOUT_S)
    return True


def mqtt_derrubar(publisher):
    """Fecha o socket sem mandar DISCONNECT (numa conexão morta a escrita travaria)."""
    try:
        publisher.mqtt.sock.close()
    except Exception:
        pass
    publisher.connected = False


def pingresp_chegou(mqtt):
    """Lê sem bloquear; True se chegou um PINGRESP (0xD0 0x00). Só assinantes
    recebem outros pacotes, e o gateway não assina nada."""
    sock = mqtt.sock
    sock.setblocking(False)
    try:
        b = sock.read(2)
    except OSError:
        b = None
    finally:
        sock.settimeout(SOCK_TIMEOUT_S)
    if b == b"":
        raise OSError("broker fechou a conexao")
    return bool(b) and b[0] == 0xD0


def poll_once():
    """Valores brutos do OT (usados pelos displays) ou None se ele não respondeu."""
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
        "cycle_count": regs[REG_CYCLE_COUNT],
        "auto_fase": regs[REG_AUTO_FASE],
    }


def dataset(v):
    """DataSet publicado: campos da Tabela tab:modbus_registers da dissertação
    (os mesmos que o AAS e o Node-RED consomem)."""
    dist = v["sensor_dist"]
    if dist == SENSOR_SEM_LEITURA:
        sensor = DataValue(None, StatusCode.BAD_SENSOR_FAILURE)
        peca = DataValue(False, StatusCode.UNCERTAIN)
    else:
        sensor = dist
        peca = dist < PECA_LIMIAR_CM

    return {
        "JointBase": float(v["base_ang"]),               # graus
        "JointShoulder": float(v["ombro_ang"]),
        "JointElbow": float(v["cotovelo_ang"]),
        "JointGripper": float(v["garra_ang"]),
        "ConveyorSpeed": v["esteira_vel"],               # %
        "ConveyorRunning": v["esteira_state"] != 0,
        "SensorDistance": sensor,                        # cm
        "PieceDetected": peca,
        "CycleCount": v["cycle_count"],
        "AutoPhase": v["auto_fase"],                     # auto_fase_t do OT
    }


def main():
    lcd = lcd_saudacao()
    nokia = nokia_init()
    # O roteador da célula também demora a ligar: insiste no Wi-Fi
    while True:
        try:
            sta = wifi_connect(WIFI_SSID, WIFI_PASSWORD)
            break
        except Exception as e:   # timeout ou erro interno do Wi-Fi do ESP32
            print("[wifi]", repr(e), "- nova tentativa")
            mostra(lcd, nokia, "Sem WiFi", WIFI_SSID, "sem wifi")
            # Desliga e religa a interface para limpar o estado do driver
            sta = network.WLAN(network.STA_IF)
            sta.active(False)
            time.sleep_ms(500)
    mostra(lcd, nokia, "WiFi conectado", sta.ifconfig()[0], "wifi ok")
    ntp_ok = ntp_sync(NTP_HOST)

    mqtt_client = MQTTClient(
        "esp32-it-modbus-gateway", MQTT_BROKER, port=MQTT_PORT,
        user=MQTT_USER, password=MQTT_PASSWORD, keepalive=MQTT_KEEPALIVE_S,
    )
    publisher = OPCUAPublisher(PUBLISHER_ID, mqtt_client, base_topic=MQTT_TOPIC)

    # O ESP32 liga bem antes do RPi (broker): tenta até conseguir
    while not mqtt_conectar(publisher):
        print("[IT] broker", MQTT_BROKER, "indisponivel, nova tentativa em", RECONNECT_MS, "ms")
        mostra(lcd, nokia, "Sem broker", MQTT_BROKER, "sem mqtt")
        time.sleep_ms(RECONNECT_MS)
    if not ntp_ok:
        ntp_ok = ntp_sync(NTP_HOST)
    mostra(lcd, nokia, "MQTT conectado", MQTT_BROKER, "mqtt ok")
    time.sleep(1)

    print("[IT] Loop iniciado. Publisher ID =", PUBLISHER_ID, "Topic =", MQTT_TOPIC)
    quadro = 0
    t_lcd = 0
    t_ping = t_resp = t_tentativa = t_ntp = time.ticks_ms()
    while True:
        values = poll_once()
        agora = time.ticks_ms()
        if sta.isconnected() and time.ticks_diff(agora, t_ntp) >= NTP_RESYNC_MS:
            t_ntp = agora
            ntp_ok = ntp_sync(NTP_HOST)
        if publisher.connected:
            ok = values is None or publisher.publish(DATASET_WRITER_ID, dataset(values))
            try:
                if pingresp_chegou(publisher.mqtt):
                    t_resp = agora
                if time.ticks_diff(agora, t_ping) >= PING_MS:
                    publisher.mqtt.ping()
                    t_ping = agora
            except OSError as e:
                print("[IT] erro na conexao MQTT:", e)
                ok = False
            if time.ticks_diff(agora, t_resp) > PING_TIMEOUT_MS:
                print("[IT] broker sem resposta ha", time.ticks_diff(agora, t_resp) // 1000, "s")
                ok = False
            if not ok:
                # Broker caiu ou conexão morta: reconecta sem parar o polling
                mqtt_derrubar(publisher)
                t_tentativa = agora
        elif time.ticks_diff(agora, t_tentativa) >= RECONNECT_MS:
            t_tentativa = agora
            if mqtt_conectar(publisher):
                t_ping = t_resp = time.ticks_ms()
                if not ntp_ok:
                    ntp_ok = ntp_sync(NTP_HOST)
        quadro += 1
        try:
            if nokia:
                painel.nokia_desenha(nokia, values, sta.isconnected(), publisher.connected,
                                     values is not None, quadro)
            if lcd and time.ticks_diff(time.ticks_ms(), t_lcd) > 1000:
                painel.lcd_telemetria(lcd, values)
                t_lcd = time.ticks_ms()
        except Exception as e:
            print("[display] erro:", e)
        time.sleep_ms(POLL_INTERVAL_MS)


if __name__ == "__main__":
    main()
