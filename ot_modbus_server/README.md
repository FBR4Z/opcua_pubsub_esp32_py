# OT Modbus Server (ESP32, ESP-IDF)

Lado OT da célula robótica da dissertação: um ESP32 com ESP-IDF 6.1 que controla o braço
(4 servos), a esteira, o sensor HC-SR04, o LCD e os botões da IHM, e expõe o estado como
**servidor Modbus RTU**. O gateway IT em MicroPython ([examples/modbus_gateway](../examples/modbus_gateway))
lê esses registradores e publica em OPC UA PubSub (MQTT).

```
ESP32 OT (este firmware)  --Modbus RTU-->  ESP32 IT (modbus_gateway)  --OPC UA PubSub/MQTT-->  broker
```

## Modbus RTU

- Endereço do escravo: 1, 115200 baud, UART com TX = GPIO17 e RX = GPIO16 (conector J7).
- Holding registers (função 0x03), definidos em [main/modbus_params.h](main/modbus_params.h):

| Offset | Conteúdo |
|---|---|
| 0 | ângulo do servo Base (graus, 0-180) |
| 1 | ângulo do servo Ombro |
| 2 | ângulo do servo Cotovelo |
| 3 | ângulo do servo Garra |
| 4 | velocidade da esteira (%, 0-100) |
| 5 | estado da esteira (0 = parada, 1 = girando) |
| 6 | distância do HC-SR04 (cm) |

## Pinagem (circuito montado)

| Função | GPIO |
|---|---|
| Servos Base / Ombro / Cotovelo / Garra (LEDC) | 13 / 14 / 27 / 26 |
| Esteira ENA / IN1 / IN2 | 32 / 33 / 25 |
| HC-SR04 TRIG / ECHO (divisor 1k/2k) | 23 / 15 |
| LCD I2C SDA / SCL | 21 / 22 |
| Botões IHM: ciclar eixo / + / − | 34 / 35 / 36 |
| Modbus TX / RX | 17 / 16 |

## Console

Na UART0 (monitor serial) há um console `ot>` com os comandos `eixo`, `ir`, `soltar` e
`esteira` (use `help`). Eles movem o braço e a esteira: cuidado com a célula montada.
No boot os servos ficam soltos e a esteira parada.

## Compilar e gravar

```
idf.py set-target esp32
idf.py build
idf.py -p COM3 flash monitor
```

As dependências (`espressif/esp-modbus`) são baixadas pelo gerenciador de componentes para
`managed_components/` (versões fixadas em `dependencies.lock`). Em placas com CP210x em que o
DTR não aciona o GPIO0, segure o botão BOOT durante o "Connecting...".
