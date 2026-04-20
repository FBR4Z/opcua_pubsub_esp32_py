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
                                              ▼
                                    AASX Package Explorer
                                    (visualização AAS V3)
```

## Arquitetura

O exemplo demonstra a **camada IT** de uma arquitetura industrial com separação OT/IT:

- **ESP32 IT** publica dados operacionais como mensagens OPC UA PubSub JSON (IEC 62541-14 §7.2.3) sobre MQTT
- **AAS Gateway** subscribe no tópico MQTT, parseia as NetworkMessages OPC UA PubSub, e popula um AAS usando o Eclipse BaSyx Python SDK
- O AAS é exportado como `.aasx` (padrão IDTA) e `.json`, visualizável no AASX Package Explorer

A biblioteca OPC UA PubSub (`opcua_pubsub.py`) é a camada central de interoperabilidade — padroniza os dados do chão de fábrica no formato IEC 62541-14, permitindo que qualquer consumidor compatível (AAS, SCADA, dashboard) interprete os dados sem conhecimento prévio da fonte.

## Estrutura do AAS

| Submodel | Conteúdo |
|----------|----------|
| **Nameplate** | Fabricante, tipo do ativo, protocolo de comunicação, método de separação OT/IT |
| **OperationalData** | JointBase, JointShoulder, JointElbow, JointGripper (rad), ConveyorRunning, PieceDetected (bool), CycleCount, LastUpdate |
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
| `main.py` | Esta pasta | Simulador da célula + publisher |
| `config.py` | Copiar de `config_example.py` | Credenciais WiFi/MQTT |

### Software (PC)
| Pacote | Versão | Propósito |
|--------|--------|-----------|
| basyx-python-sdk | ≥2.0.0 | Metamodelo AAS + exportação AASX |
| paho-mqtt | ≥2.0.0 | Subscrição MQTT |
| AASX Package Explorer | V3.x | Visualização do AAS (opcional) |
| Mosquitto | 2.x | Broker MQTT |

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

Baixe o [AASX Package Explorer](https://github.com/eclipse-aaspe/package-explorer/releases) e abra `celula_robotica.aasx`.

## Mapeamento de Tipos de Dados

O gateway realiza a conversão entre tipos OPC UA (Part 6) e tipos AAS/XSD:

| Tipo OPC UA | Tipo AAS (XSD) | Campos |
|-------------|----------------|--------|
| Float | xs:double | JointBase, JointShoulder, JointElbow, JointGripper |
| Boolean | xs:boolean | ConveyorRunning, PieceDetected |
| Integer | xs:integer | CycleCount |
| String | xs:string | LastUpdate |

## Contexto Acadêmico

Este exemplo faz parte de uma **dissertação de Mestrado** em Engenharia Elétrica na **UEA (Universidade do Estado do Amazonas)**. Demonstra a biblioteca OPC UA PubSub como camada de interoperabilidade entre o chão de fábrica (OT) e o gêmeo digital (IT), seguindo princípios de separação OT/IT da IEC 62443.

## Licença

Licença MIT — veja [LICENSE](../../LICENSE) para detalhes.