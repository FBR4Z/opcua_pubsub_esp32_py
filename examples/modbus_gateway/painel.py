"""
Paineis do gateway IT.

- Nokia 5110 (84x48): painel grafico (braco robotico vendo de lado, mostrador
  da base, barra do sensor, esteira animada e icones de status).
- LCD 16x2: telemetria numerica e mensagens de boot.
"""

import math

COS = math.cos
SIN = math.sin


def _rad(a):
    return a * math.pi / 180


# ------------------------------------------------------------------
# Nokia 5110
# ------------------------------------------------------------------
def _icone_wifi(d, x, y, ok):
    if ok:
        d.fill_rect(x, y + 5, 2, 2, 1)
        d.fill_rect(x + 2, y + 3, 2, 4, 1)
        d.fill_rect(x + 4, y + 1, 2, 6, 1)
    else:
        d.hline(x, y + 6, 6, 1)
        d.line(x, y, x + 5, y + 5, 1)


def _icone_mqtt(d, x, y, ok, pulso):
    d.rect(x, y, 7, 7, 1)
    if ok:
        d.fill_rect(x + 2, y + 2, 3, 3, 1 if pulso else 0)
    else:
        d.line(x, y, x + 6, y + 6, 1)


def _icone_ot(d, x, y, ok):
    d.fill_rect(x, y + 2, 2, 3, 1)
    d.fill_rect(x + 5, y + 2, 2, 3, 1)
    if ok:
        d.hline(x + 2, y + 3, 3, 1)
    else:
        d.pixel(x + 3, y + 3, 1)


def _braco(d, v):
    px, py = 23, 40
    d.fill_rect(8, 43, 30, 4, 1)          # chao
    d.fill_rect(19, 39, 9, 4, 1)          # pedestal
    a1 = _rad(v["ombro_ang"])
    x1 = px + 12 * COS(a1)
    y1 = py - 12 * SIN(a1)
    a2 = a1 + _rad(v["cotovelo_ang"] - 90)
    x2 = x1 + 10 * COS(a2)
    y2 = y1 - 10 * SIN(a2)
    ix1, iy1, ix2, iy2 = int(x1), int(y1), int(x2), int(y2)
    d.line(px, py, ix1, iy1, 1)
    d.line(px + 1, py, ix1 + 1, iy1, 1)
    d.line(ix1, iy1, ix2, iy2, 1)
    d.line(ix1 + 1, iy1, ix2 + 1, iy2, 1)
    d.fill_rect(px - 1, py - 1, 3, 3, 1)  # articulacoes
    d.fill_rect(ix1 - 1, iy1 - 1, 3, 3, 1)
    # garra: duas pincas abrindo conforme o angulo
    abre = _rad(8 + v["garra_ang"] * 0.3)
    for s in (-1, 1):
        a = a2 + s * abre
        d.line(ix2, iy2, int(ix2 + 5 * COS(a)), int(iy2 - 5 * SIN(a)), 1)


def _mostrador_base(d, ang):
    cx, cy, r = 66, 24, 12
    for t in range(0, 181, 15):
        d.pixel(int(cx + r * COS(_rad(t))), int(cy - r * SIN(_rad(t))), 1)
    d.hline(cx - r, cy, 2 * r + 1, 1)
    a = _rad(max(0, min(180, ang)))
    d.line(cx, cy, int(cx + (r - 2) * COS(a)), int(cy - (r - 2) * SIN(a)), 1)
    d.fill_rect(cx - 1, cy - 1, 3, 3, 1)


def _sensor_esteira(d, v, quadro):
    dist = v["sensor_dist"]
    d.rect(50, 30, 34, 5, 1)              # barra de distancia (0..100 cm)
    cheio = min(dist, 100) * 32 // 100
    if cheio > 0:
        d.fill_rect(51, 31, cheio, 3, 1)
    d.rect(50, 41, 34, 6, 1)              # esteira
    if v["esteira_state"]:
        off = (quadro * 2) % 6
        for x in range(51 + off, 83, 6):
            d.vline(x, 43, 2, 1)
    else:
        d.hline(51, 44, 32, 1)
    if dist < 25:                         # objeto proximo ao sensor
        d.fill_rect(62, 36, 10, 4, 1)


def nokia_desenha(d, v, wifi_ok, mqtt_ok, ot_ok, quadro):
    """v: dict de valores do OT ou None se o OT nao respondeu."""
    d.fill(0)
    d.text("GATEWAY", 0, 0, 1)
    _icone_wifi(d, 58, 0, wifi_ok)
    _icone_mqtt(d, 66, 0, mqtt_ok, quadro % 2 == 0)
    _icone_ot(d, 76, 0, ot_ok)
    d.hline(0, 9, 84, 1)
    if v is None:
        d.text("SEM", 12, 18, 1)
        d.text("RESPOSTA", 2, 28, 1)
    else:
        _braco(d, v)
        _mostrador_base(d, v["base_ang"])
        _sensor_esteira(d, v, quadro)
    d.show()


def nokia_boot(d, linha1, linha2=""):
    d.fill(0)
    d.rect(0, 0, 84, 48, 1)
    d.text("IT v2", 21, 6, 1)
    d.hline(8, 17, 68, 1)
    d.text("Modbus", 18, 22, 1)
    d.text("> OPC UA", 10, 31, 1)
    d.text(linha1[:10], 2, 40, 1)
    d.show()


# ------------------------------------------------------------------
# LCD 16x2
# ------------------------------------------------------------------
def lcd_telemetria(lcd, v):
    if v is None:
        lcd.print_line(0, "OT sem resposta")
        lcd.print_line(1, "Verifique RS485")
        return
    lcd.print_line(0, "B%3d O%3d C%3d" % (v["base_ang"], v["ombro_ang"], v["cotovelo_ang"]))
    lcd.print_line(1, "G%3d D%3dcm %s" % (v["garra_ang"], v["sensor_dist"],
                                          "ON " if v["esteira_state"] else "OFF"))
