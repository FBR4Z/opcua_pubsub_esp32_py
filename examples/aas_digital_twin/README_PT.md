# OPC UA PubSub → Asset Administration Shell (AAS)

Demonstração prática da biblioteca OPC UA PubSub alimentando um Asset Administration Shell (AAS) como gêmeo digital de uma célula robótica, utilizando Eclipse BaSyx Python SDK.

```
  ESP32 IT (MicroPython)              PC (Python)
┌───────────────────────┐    MQTT    ┌──────────────────────────┐
│ opcua_pubsub.py       │──────────►│ aas_gateway.py           │
│ (IEC 62541-14 JSON)   │           │ (BaSyx Python SDK)       │
│                       │           │                          │
│ Simula:               │           │ Cria AAS com:            │
│  • Joints braço 4DOF  │           │  • Nameplate             │
│  • Esteira            │           │  • OperationalData       │
│  • Detecção de peça   │           │  • OPCUAPubSubInfo       │
│  • Ciclo pick-and-    │           │                          │
│    place              │           │ Exporta: .aasx + .json   │
└───────────────────────┘           └──────────────────────────┘
                                              │
                              ┌───────────────┴───────────────┐
                              ▼                               ▼
                 Eclipse BaSyx (API AAS Part 2)     AASX Package Explorer
                 + AAS Web UI (ao vivo)             (arquivo .aasx)
```

Na célula real, quem publica é o gateway IT ([examples/modbus_gateway](../modbus_gateway/README.md))
com os dados do controlador OT, e o `aas_gateway.py` roda como serviço no RPi 5 da célula
([deploy/rpi5](../../deploy/rpi5/README.md)). O `main.py` desta pasta é um **simulador** da célula,
útil para testar sem o hardware. Visão geral: [docs/CELULA_ROBOTICA.md](../../docs/CELULA_ROBOTICA.md).

## Arquitetura

O exemplo demonstra a **camada IT** de uma arquitetura industrial com separação OT/IT:

- **ESP32 IT** publica dados operacionais como mensagens OPC UA PubSub JSON (IEC 62541-14 §7.2.3) sobre MQTT
- **AAS Gateway** subscribe no tópico MQTT, parseia as NetworkMessages OPC UA PubSub, e popula um AAS usando o Eclipse BaSyx Python SDK
- O AAS é publicado no **Eclipse BaSyx** pela API REST da AAS Part 2 (shell e submodelos na partida,
  `OperationalData` e `OPCUAPubSubInfo` 1x por segundo) e visto ao vivo na AAS Web UI
- O AAS também é exportado como `.aasx` (padrão IDTA) e `.json` a cada 60 s, para o AASX Package Explorer

A biblioteca OPC UA PubSub (`opcua_pubsub.py`) é a camada central de interoperabilidade — padroniza os dados do chão de fábrica no formato IEC 62541-14, permitindo que qualquer consumidor compatível (AAS, SCADA, dashboard) interprete os dados sem conhecimento prévio da fonte.

## Estrutura do AAS

| Submodel | Conteúdo |
|----------|----------|
| **Nameplate** | Fabricante, tipo do ativo, protocolo de comunicação, método de separação OT/IT |
| **OperationalData** | JointBase, JointShoulder, JointElbow, JointGripper (graus), ConveyorSpeed (%), ConveyorRunning, SensorDistance (cm), PieceDetected, CycleCount, AutoPhase, LastUpdate (UTC) |
| **OPCUAPubSubInfo** | PublisherId, tópico MQTT, encoding, MessageType, DataSetWriterId, MessagesReceived |

## Requisitos

### Hardware
| Componente | Descrição |
|------------|-----------|
| ESP32 | Qualquer variante com WiFi |
| PC | Windows/Linux com Python 3.10+ |

### Software (ESP32)
| Arquivo | Origem | Descrição |
|---------|--------|-----------|
| `opcua_pubsub.py` | `src/opcua_pubsub.py` | Biblioteca OPC UA PubSub |
| `main.py` | Esta pasta | Simulador da célula + publisher (juntas ainda em rad; a célula real usa graus) |
| `config.py` | Copiar de `config_example.py` | Credenciais WiFi/MQTT |

### Software (RPi 5 da célula, ou PC)
| Pacote | Versão | Propósito |
|--------|--------|-----------|
| basyx-python-sdk | ≥2.0.0 (2.2.0 no RPi) | Metamodelo AAS + exportação AASX |
| paho-mqtt | ≥2.0.0 | Subscrição MQTT |
| Mosquitto | 2.x | Broker MQTT |
| Eclipse BaSyx (Docker) | AAS Environment 2.0.0-milestone-16 | Servidor AAS (opcional; `BASYX_URL = ""` desliga) |
| AASX Package Explorer | V3.x | Visualização do arquivo AAS (opcional) |

Configuração no topo do `aas_gateway.py`: `MQTT_BROKER`, `MQTT_TOPIC`, `BASYX_URL`
(`http://127.0.0.1:8081`), `BASYX_INTERVAL_S` (1 s) e `AASX_INTERVAL_S` (60 s).

## Instalação e Uso

### 1. Instalar dependências no PC

```bash
pip install basyx-python-sdk paho-mqtt
```

### 2. Configurar ESP32

```bash
cp config_example.py config.py
# Edite config.py com seu WiFi e IP do broker
```

Faça upload para o ESP32 (via Thonny ou mpremote):
- `config.py`
- `main.py`
- `opcua_pubsub.py` (da pasta `src/`)

### 3. Iniciar broker Mosquitto

Certifique-se que o Mosquitto está rodando no PC (porta 1883).

### 4. Rodar o AAS Gateway

```bash
python aas_gateway.py
```

### 5. Reiniciar o ESP32

O ESP32 começará a publicar dados simulados da célula robótica.

### 6. Visualizar o AAS

- **Ao vivo:** AAS Web UI do BaSyx (na célula, `http://169.254.14.189:3000`). A Web UI consulta a
  API REST (pull): recarregue a página ou ligue o "Auto Sync" nas configurações dela.
- **API:** `GET http://<servidor>:8081/submodels/<id em base64url>/$value`.
- **Arquivo:** [AASX Package Explorer](https://github.com/eclipse-aaspe/package-explorer/releases) →
  abrir `celula_robotica.aasx` (foto do momento; regravado a cada 60 s).

Na célula, o `aas_gateway.py` roda como serviço systemd (`aas-gateway`) e o BaSyx via
`docker compose`: ver [deploy/rpi5/README.md](../../deploy/rpi5/README.md).

## Mapeamento de Tipos de Dados

O gateway realiza a conversão entre tipos OPC UA (Part 6) e tipos AAS/XSD:

| Tipo OPC UA | Tipo AAS (XSD) | Campos |
|-------------|----------------|--------|
| Float | xs:double | JointBase, JointShoulder, JointElbow, JointGripper |
| Boolean | xs:boolean | ConveyorRunning, PieceDetected |
| Integer | xs:int | ConveyorSpeed, SensorDistance, CycleCount, AutoPhase |
| String | xs:string | LastUpdate |

## Contexto Acadêmico

Este exemplo faz parte de uma **dissertação de Mestrado** em Engenharia Elétrica na **UEA (Universidade do Estado do Amazonas)**. Demonstra a biblioteca OPC UA PubSub como camada de interoperabilidade entre o chão de fábrica (OT) e o gêmeo digital (IT), seguindo princípios de separação OT/IT da IEC 62443.

## Licença

Licença MIT — veja [LICENSE](../../LICENSE) para detalhes.