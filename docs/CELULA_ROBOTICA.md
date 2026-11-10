# Célula robótica: pilha OT/IT completa

Visão geral da célula montada para a dissertação: do controlador de chão de fábrica (OT) até o
gêmeo digital (AAS), passando pela biblioteca OPC UA PubSub deste repositório.
Estado em 2026-11-09: **funcionando de ponta a ponta com dados reais**.

```
 Camada OT                 Camada IT (borda)            Servidor da célula (RPi 5 "AAS")         PC
┌──────────────────┐ J7  ┌───────────────────┐ Wi-Fi ┌──────────────────────────────────┐ cabo ┌──────────────┐
│ ESP32 OT         │─────│ ESP32 IT          │ OPC_UA│ Mosquitto :1883                  │ eth0 │ navegador    │
│ ESP-IDF 6.1      │Modbus│ MicroPython       │──────►│  ├─► aas-gateway ─► BaSyx :8081  │─────►│ Prosys OPC UA│
│ 4 servos,        │ RTU │ gateway Modbus →  │ MQTT  │  │    (AAS Part 2)   Web UI :3000 │      │ Browser      │
│ esteira, HC-SR04,│     │ OPC UA PubSub JSON│       │  └─► Node-RED :1880 (dashboard)  │      │ AASX Explorer│
│ LCD, botões IHM  │     │ LCD + Nokia 5110  │       │ chrony (NTP) ◄──────────────────────── w32time │
└──────────────────┘     └───────────────────┘       └──────────────────────────────────┘      └──────────────┘
  ot_modbus_server/        examples/modbus_gateway/     deploy/rpi5/                            deploy/pc/
```

- **Separação OT/IT:** o TO só fala Modbus RTU pelo cabo serial J7 (TX, RX, GND). Não tem rede.
  O fluxo é **só de leitura**: nenhum consumidor de TI comanda o braço.
- **Desacoplamento:** AAS, Node-RED e Prosys consomem a **mesma** mensagem OPC UA PubSub, sem
  nenhuma adaptação no publicador.

## Endereços

| Equipamento | Rede | Endereço |
|---|---|---|
| Roteador da célula (Claro/NET, página "Gateways") | SSID `OPC_UA` (sem internet); DHCP só de `.100` a `.254` | `192.168.0.1` |
| RPi 5 `AAS`, `wlan0` | `OPC_UA` | **`192.168.0.2`** (fixo): broker MQTT e NTP dos ESP32 |
| RPi 5 `AAS`, `eth0` | cabo direto ao PC | **`169.254.14.189`** (fixo) |
| PC, placa `Ethernet` | cabo direto ao RPi | **`169.254.124.59`** (fixo) |
| ESP32 IT | `OPC_UA` | DHCP (`192.168.0.100` em 2026-11-09) |
| ESP32 OT | — | sem rede; Modbus RTU escravo 1, 115200 8N1 |

De `.2` a `.99` ficam livres para IPs fixos: o DHCP do roteador foi limitado a `.100`–`.254`
(Redes → LAN/DHCP: início `.100`, 155 CPEs, lease 86400 s). Antes ele começava em `.2` e, no boot
a frio, entregou o `.2` (IP fixo do RPi) para o ESP32 IT, que passou a procurar o broker nele
mesmo ("sem broker").

Atenção: a rede de casa também usa `192.168.0.x`. Um ESP32 que fique na rede errada encontra
"outro" `192.168.0.2` (ver [gateway IT](../examples/modbus_gateway/README.md)).

## Serviços e onde ver os dados

| O quê | Onde | Tipo |
|---|---|---|
| Dashboard Node-RED | http://169.254.14.189:1880/dashboard/celula | push (MQTT) |
| Editor Node-RED | http://169.254.14.189:1880 | — |
| AAS Web UI (BaSyx) | http://169.254.14.189:3000 | pull (REST) |
| API do AAS (Part 2) | http://169.254.14.189:8081/shells, `/submodels` | pull (REST) |
| Arquivo AAS | `~/aas/celula_robotica.aasx` no RPi (a cada 60 s), abre no AASX Package Explorer | foto |
| Prosys OPC UA Browser | PubSub, ver abaixo | push (MQTT) |
| Área de trabalho do RPi | `mstsc` → `169.254.14.189`, usuário `engfb` (sair pelo menu Logout) | — |
| Página do roteador | Chromium **no RPi** (mstsc) → `http://192.168.0.1` (recusa acesso por túnel) | — |
| Terminal do RPi | `ssh rpi5` (aponta para `169.254.14.189`) | — |

**Push × pull.** Node-RED e Prosys *assinam* o tópico MQTT e recebem cada mensagem na hora. A AAS
Web UI *consulta* o servidor pela API REST: ela só mostra valores novos quando a página é
recarregada ou com o "Auto Sync" ligado nas configurações da Web UI. No servidor, o AAS é
atualizado 1x por segundo. Os dois padrões são complementares: eventos (OPC UA PubSub) no
transporte e consulta sob demanda (AAS Part 2) no gêmeo digital.

### Prosys OPC UA Browser (assinante PubSub)

Testado em 2026-11-09 com o Prosys OPC UA Browser 2026.2 do PC, sem servidor OPC UA, direto no
PubSub:

| Campo | Valor |
|---|---|
| Transporte / codificação | MQTT / JSON |
| Broker | `mqtt://169.254.14.189:1883` (pelo cabo), sem usuário |
| Tópico | `it/opcua/celula_robotica` |
| PublisherId | `urn:uea:celula-robotica:esp32-it` (String) |
| DataSetWriterId | `2000` |

## Mensagem OPC UA PubSub (DataSet da célula)

NetworkMessage JSON (IEC 62541-14 §7.2.3), `MessageType = "ua-data"`, uma DataSetMessage por
mensagem, ~2,8 por segundo (medido: um ciclo a cada ~360 ms = 200 ms de espera + Modbus +
display Nokia + publicação). Cada campo é um DataValue com `Value` e
`SourceTimestamp` (UTC, hora acertada pelo RPi). O `StatusCode` só aparece quando não é Good.
Os campos seguem a Tabela `tab:modbus_registers` da dissertação.

| Registrador (OT) | Campo | Tipo | Unidade / observação |
|---|---|---|---|
| 0 `BASE_ANG` | `JointBase` | Double | graus (0–180) |
| 1 `OMBRO_ANG` | `JointShoulder` | Double | graus |
| 2 `COTOVELO_ANG` | `JointElbow` | Double | graus |
| 3 `GARRA_ANG` | `JointGripper` | Double | graus (aberta 90, fechada 180) |
| 4 `ESTEIRA_VEL` | `ConveyorSpeed` | Int | % (0–100) |
| 5 `ESTEIRA_STATE` | `ConveyorRunning` | Boolean | |
| 6 `SENSOR_DIST` | `SensorDistance` | Int | cm; `0xFFFF` → `Value: null`, `StatusCode` BadSensorFailure |
| 6 (derivado) | `PieceDetected` | Boolean | `SensorDistance < 8` cm (limiar do OT); Uncertain sem leitura |
| 7 `CYCLE_COUNT` | `CycleCount` | Int | ciclos *pick-and-place* completos |
| 8 `AUTO_FASE` | `AutoPhase` | Int | 0 parado, 1 aguarda peça + botão A, 2 pega, 3 transporta, 4 solta, 5 esteira |

Exemplo (resumido):

```json
{"MessageId": "75", "MessageType": "ua-data",
 "PublisherId": "urn:uea:celula-robotica:esp32-it",
 "Messages": [{"DataSetWriterId": 2000, "SequenceNumber": 75,
   "Payload": {
     "JointBase":      {"Value": 90.0, "SourceTimestamp": "2026-11-10T01:17:01Z"},
     "SensorDistance": {"Value": 6,    "SourceTimestamp": "2026-11-10T01:17:01Z"},
     "PieceDetected":  {"Value": true, "SourceTimestamp": "2026-11-10T01:17:01Z"},
     "CycleCount":     {"Value": 0,    "SourceTimestamp": "2026-11-10T01:17:01Z"}}}]}
```

## AAS (gêmeo digital)

`aas_gateway.py` (serviço `aas-gateway` no RPi) assina o tópico, monta o AAS com o BaSyx Python
SDK e o publica no **Eclipse BaSyx** (AAS Environment 2.0.0-milestone-16, Docker) pela API REST
da AAS Part 2: PUT do shell e dos submodelos (POST se ainda não existirem), depois só
`OperationalData` e `OPCUAPubSubInfo` 1x por segundo. O BaSyx guarda tudo em memória; se ele
reiniciar, o gateway reenvia o AAS inteiro sozinho.

| Submodelo | Conteúdo |
|---|---|
| `Nameplate` | fabricante (UEA), tipo do ativo, protocolo, separação OT/IT |
| `OperationalData` | os 10 campos da tabela acima + `LastUpdate` (UTC) |
| `OPCUAPubSubInfo` | PublisherId, tópico, codificação, MessageType, DataSetWriterId, mensagens recebidas |

Valores ao vivo pela API (`<id>` = id do submodelo em base64url, sem `=`):

```
GET http://169.254.14.189:8081/submodels/<id>/$value
# OperationalData: urn:uea:celula-robotica:submodel:operational-data
#   -> dXJuOnVlYTpjZWx1bGEtcm9ib3RpY2E6c3VibW9kZWw6b3BlcmF0aW9uYWwtZGF0YQ
```

## Hora (NTP)

PC (w32time, sincronizado com `a.ntp.br`) → RPi (`chrony`, pelo cabo) → ESP32 IT (`ntptime` no
boot). Diferença PC↔RPi da ordem de 0,1 ms; o `SourceTimestamp` do ESP32 bate no segundo com o
RPi. Detalhes em [deploy/rpi5/README.md](../deploy/rpi5/README.md#hora-ntp).

## Boot e recuperação

| Situação | Comportamento |
|---|---|
| ESP32 IT liga antes do roteador | tenta o Wi-Fi até conseguir |
| ESP32 IT liga antes do RPi | tenta o broker a cada 3 s; NTP de novo quando o broker aparece |
| ESP32 IT ficou em outra rede (soft reset) | sai dela e entra na `OPC_UA` |
| Broker cai e a publicação dá erro | reconecta a cada 3 s, sem parar o polling Modbus |
| Conexão TCP "meio morta" (RPi trocou de rede, pacotes somem) | PINGREQ a cada 5 s; sem PINGRESP em 12 s, ou escrita parada há 2 s, derruba e reconecta. Volta ~2 s depois de o caminho voltar |
| RPi reinicia | Mosquitto, Node-RED, aas-gateway, chrony e BaSyx (Docker) sobem sozinhos; `wlan0` volta para a `OPC_UA` |
| RPi liga sem a hora certa (sem bateria no RTC) | `chrony` corrige ~20 s depois do boot; as primeiras mensagens do AAS podem sair com hora errada |
| BaSyx reinicia ou sobe depois do aas-gateway | o aas-gateway reenvia o AAS inteiro (tenta a cada 1 s, mesmo sem mensagens) |
| RPi liga antes do roteador | `wlan0` conecta quando o roteador aparece; com `ipv6.method link-local` não fica esperando IPv6 |

## Testes realizados (2026-11-09)

| Teste | Resultado |
|---|---|
| Reboot do RPi (rede fixa, serviços) | ok: tudo voltou sozinho; o chrony corrigiu um atraso de 3035 s no relógio |
| Modbus IT↔OT pelo cabo J7 | ok: 10/10 leituras dos 9 registradores |
| ESP32 IT → Wi-Fi `OPC_UA` → NTP → broker | ok |
| AAS (arquivo e BaSyx) e Node-RED com dados reais | ok |
| Ciclo automático pelos botões da IHM | ok: `CycleCount` subiu para 6 no AAS |
| Boot a frio de tudo junto (1ª vez) | serviços, BaSyx, dashboard e hora ok; **falhou** a rede: o RPi ficou esperando IPv6 sem aplicar o IPv4, o roteador deu o `.2` ao ESP32 IT e o AAS não foi reenviado ao BaSyx. Corrigido (IPv6 link-local, DHCP a partir de `.100`, reenvio do AAS a cada 1 s) |
| Reset da placa IT com o DHCP novo (2x) | voltou a publicar em ~5 s, sempre como `192.168.0.100` |
| Prosys OPC UA Browser assinando o PubSub JSON | ok |
| RPi saiu e voltou para a `OPC_UA` com o ESP32 publicando | voltou sozinho, mas só depois de ~5 min (antes da correção abaixo) |
| Tráfego com o ESP32 bloqueado 25 s no RPi (`iptables DROP`), com o vigia de ping | voltou **2 s** depois de liberar |
| Taxa de publicação | 56 mensagens em 20 s (2,8/s) |

## Pendências

- **Servo da garra quebrado (2026-11-09):** faz barulho mas não gira; trocar. Depois da troca,
  conferir as posições aberta (90) e fechada (180) no console `ot>` do OT antes de rodar o automático.
- Gateway IT: enquanto o broker está inalcançável, cada tentativa de `connect()` (sem prazo no
  `umqtt`) pode segurar o laço; Modbus e displays param até ela terminar.
- Repetir o boot a frio de tudo junto, agora com as correções da 1ª tentativa.
- Hora no boot do RPi: `After=time-sync.target` + `chrony-wait` nos serviços, ou bateria ML-2020 no RTC.
- Senha no Mosquitto antes de sair da fase de testes.
- Simulador `examples/aas_digital_twin/main.py` ainda publica as juntas em rad (a célula real e o AAS usam graus).
- Dissertação: texto do simulador ("em rad"), figura das fases do ciclo, AAS como servidor BaSyx
  (antes só arquivo), push × pull, capturas de tela (dashboard, flow, Prosys, AAS Web UI, AASX Explorer).

## Arquivos

| Pasta | Conteúdo |
|---|---|
| [ot_modbus_server/](../ot_modbus_server/README.md) | firmware OT (ESP-IDF): registradores, pinagem, ciclo automático |
| [examples/modbus_gateway/](../examples/modbus_gateway/README.md) | gateway IT (MicroPython) |
| [examples/aas_digital_twin/](../examples/aas_digital_twin/README_PT.md) | `aas_gateway.py` (AAS) e simulador |
| [deploy/rpi5/](../deploy/rpi5/README.md) | instalação do RPi: Mosquitto, Node-RED (flow), BaSyx, chrony, rede |
| [deploy/pc/](../deploy/pc/) | scripts do PC: servidor NTP do Windows e IP fixo do cabo |
