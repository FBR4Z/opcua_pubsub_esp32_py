# Gateway IT: Modbus RTU → OPC UA PubSub (MicroPython)

Firmware da placa IT da célula robótica. Lê o controlador OT
([ot_modbus_server](../../ot_modbus_server/README.md)) por Modbus RTU e publica os dados como
NetworkMessages OPC UA PubSub JSON (IEC 62541-14 §7.2.3) no broker MQTT do RPi 5.
Visão geral da célula: [docs/CELULA_ROBOTICA.md](../../docs/CELULA_ROBOTICA.md).

```
OT (escravo 1) --UART2, cabo J7, 115200 8N1--> IT --Wi-Fi OPC_UA, MQTT--> 192.168.0.2:1883
                                                                          it/opcua/celula_robotica
```

## Arquivos (todos na raiz do ESP32)

| Arquivo | Função |
|---|---|
| `main.py` | gateway: Wi-Fi → NTP → MQTT → laço de polling e publicação (~2,8 mensagens/s) |
| `config.py` | copiado de [config_example.py](config_example.py), com a senha do Wi-Fi (não vai para o git) |
| `opcua_pubsub.py` | biblioteca OPC UA PubSub JSON (cópia de `src/`) |
| `modbus_rtu_client.py` | cliente Modbus RTU (função 03, leitura de holding registers) |
| `lcd_i2c_test.py` | driver do LCD 16x2 I2C (SDA 21, SCL 22) |
| `nokia5110.py`, `painel.py` | display Nokia 5110 (J14: DIN 13, CLK 14, CE 27, DC 26, RST 25): braço, base, sensor e esteira desenhados |

Dependência: `umqtt.simple` (`import mip; mip.install("umqtt.simple")`).

## Configuração (`config.py`)

| Variável | Valor na célula |
|---|---|
| `WIFI_SSID` / `WIFI_PASSWORD` | `OPC_UA` / senha do roteador da célula |
| `MQTT_BROKER`, `MQTT_PORT` | `192.168.0.2`, `1883` (sem usuário) |
| `NTP_HOST` | `192.168.0.2` (chrony do RPi; se faltar, usa o `MQTT_BROKER`) |
| `PUBLISHER_ID` | `urn:uea:celula-robotica:esp32-it` |
| `DATASET_WRITER_ID` | `2000` |
| `MQTT_TOPIC` | `it/opcua/celula_robotica` (assinado pelo aas-gateway e pelo Node-RED) |

## DataSet publicado

Lê os 9 holding registers do OT (0–8) e publica os campos da Tabela `tab:modbus_registers` da
dissertação: `JointBase`, `JointShoulder`, `JointElbow`, `JointGripper` (graus), `ConveyorSpeed`
(%), `ConveyorRunning`, `SensorDistance` (cm), `PieceDetected` (< 8 cm), `CycleCount` e
`AutoPhase`. Sensor sem leitura (`0xFFFF`) vira `Value: null` com `StatusCode` BadSensorFailure.
Tabela completa e exemplo de mensagem em [docs/CELULA_ROBOTICA.md](../../docs/CELULA_ROBOTICA.md#mensagem-opc-ua-pubsub-dataset-da-célula).

`poll_once()` devolve os valores brutos (usados pelo LCD e pelo Nokia) e `dataset()` monta o
que é publicado. Para mudar o esquema, mexa só em `dataset()` e avise o
[aas_gateway.py](../aas_digital_twin/aas_gateway.py) e o flow do Node-RED
([deploy/rpi5/nodered-celula.json](../../deploy/rpi5/nodered-celula.json)).

## Partida e recuperação

- Wi-Fi: tenta até conseguir (o roteador demora mais que o ESP32 para ligar). Se a conexão que
  sobreviveu ao soft reset for de outro SSID, sai dela primeiro.
- NTP: acerta o RTC (UTC) pelo RPi, para o `SourceTimestamp` sair certo; tenta de novo quando o
  broker aparecer.
- MQTT: tenta o broker a cada 3 s; se uma publicação falhar, reconecta sem parar o polling.
- Vigia da conexão: com QoS 0 a publicação não tem confirmação, e uma conexão TCP "meio morta"
  (o RPi saiu da rede e voltou) não dá erro; antes levava ~5 min para ser percebida. Agora o
  gateway manda PINGREQ a cada 5 s (`PING_MS`) e lê o PINGRESP sem bloquear; sem resposta em
  12 s (`PING_TIMEOUT_MS`), ou com escrita parada há 2 s (`SOCK_TIMEOUT_S`), fecha o socket e
  reconecta. Teste com o tráfego bloqueado 25 s no RPi: voltou 2 s depois de liberar.
  `keepalive=30` faz o Mosquitto descartar a conexão velha.
- Limitação: o `connect()` do `umqtt` não tem prazo; com o broker inalcançável, cada tentativa
  pode segurar o laço (Modbus e displays) por alguns segundos.

## Gravar na placa (Thonny)

1. Copie os arquivos da tabela acima para a raiz do ESP32 (o `main.py` roda sozinho no boot).
2. Crie o `config.py` a partir do `config_example.py` e ponha a senha do Wi-Fi.
3. Teste do cabo J7 sem Wi-Fi, no REPL:
   ```python
   from modbus_rtu_client import ModbusRTUClient
   m = ModbusRTUClient(uart_id=2, tx=17, rx=16, baudrate=115200, timeout_ms=200)
   m.read_holding_registers(1, 0, 9)   # ex.: [90, 90, 90, 90, 0, 0, 8, 0, 0]
   ```

Cuidados:
- Gravando por código (`exec`), use sempre `with open(...)`: no MicroPython o arquivo só vai
  para a flash quando é fechado.
- A rede de casa também é `192.168.0.x`: no `[wifi] conectado, IP = ...` confira se o ESP32
  está mesmo na `OPC_UA`.
