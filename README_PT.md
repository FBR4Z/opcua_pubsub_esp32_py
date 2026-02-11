# OPC UA PubSub para ESP32 (MicroPython)

<p align="center">
  <img src="https://img.shields.io/badge/OPC%20UA-Part%2014-blue?style=for-the-badge" alt="OPC UA Part 14"/>
  <img src="https://img.shields.io/badge/MicroPython-1.20+-green?style=for-the-badge" alt="MicroPython"/>
  <img src="https://img.shields.io/badge/ESP32-Suportado-orange?style=for-the-badge" alt="ESP32"/>
  <img src="https://img.shields.io/badge/Licença-MIT-yellow?style=for-the-badge" alt="Licença"/>
</p>

<p align="center">
  <strong>A primeira implementação em MicroPython do OPC UA PubSub (IEC 62541-14)</strong><br>
  Habilitando IoT industrial em dispositivos com recursos limitados
</p>

<p align="center">
  🌐 <a href="README.md">English version</a>
</p>

---

## Visão Geral

Este projeto implementa o protocolo **OPC UA PubSub** (IEC 62541-14) em **MicroPython** para microcontroladores **ESP32**. Fornece codificação **JSON** e **UADP binária** sobre transporte **MQTT**, validado com ferramentas certificadas da OPC Foundation.

A biblioteca é projetada para cenários de retrofit industrial brownfield, onde adicionar conectividade OPC UA a sensores de baixo custo pode reduzir o custo por nó de €500–2000 (CLPs tradicionais) para €30–80 (ESP32 + esta biblioteca).

---

## Benchmarks de Performance

Testado em ESP32-WROOM-32 (240 MHz, MicroPython), broker Mosquitto local, fevereiro de 2026:

| Métrica | JSON | UADP Binário |
|---------|------|--------------|
| **Throughput** | 126,9 msg/s | 299,4 msg/s |
| **Tamanho da mensagem** (3 campos) | 370 B | 54 B |
| **Latência RTT** (média) | 120,8 ms | 125,5 ms |
| **Taxa de entrega** | 100% | 100% |
| **Eficiência no fio** | 1,0x | 6,9x menor |

UADP é **2,4x mais rápido** e **6,9x menor** no fio. A latência é dominada pela rede (~120 ms RTT WiFi/MQTT), tornando a diferença de codificação insignificante para mensagens individuais.

Todas as 51 mensagens UADP foram validadas em tempo real pelo **OPC Labs OpcCmd** (ferramenta certificada da OPC Foundation) durante o benchmark — zero erros de decodificação, todos StatusCode **Good**.

> Relatório completo com metodologia: [docs/BENCHMARK_REPORT.md](docs/BENCHMARK_REPORT.md)

---

## Formatos de Codificação

### Codificação JSON (IEC 62541-14 §7.2.3)

Formato legível usando JSON padrão sobre MQTT. Ideal para debugging, prototipagem e ambientes onde legibilidade importa mais que largura de banda. Compatível com qualquer cliente MQTT que possa interpretar JSON — nenhuma ferramenta OPC UA específica necessária no lado do subscriber.

```json
{
  "MessageType": "ua-data",
  "PublisherId": "ESP32-Sensor",
  "Messages": [{
    "DataSetWriterId": 1000,
    "SequenceNumber": 1,
    "Payload": {
      "Temperature": {"Value": 25.5, "SourceTimestamp": "2026-02-07T10:30:00Z"}
    }
  }]
}
```

### Codificação UADP Binária (IEC 62541-14 §7.2.2)

Formato binário compacto usando a codificação de campo Variant definida na Part 14. Validado byte-a-byte contra o OPC Labs OpcCmd. Mais adequado para redes com largura de banda limitada e aquisição de dados de alta frequência onde cada byte importa.

A implementação usa o formato de header NetworkMessage v7 com ExtendedFlags1, String PublisherId, DataSetClassId (GUID) e FieldCount — todos obrigatórios para interoperabilidade com ferramentas OPC UA certificadas.

---

## Conformidade com OPC UA Part 14

Esta implementação visa um **subconjunto funcional** da IEC 62541-14 adequado para dispositivos com recursos limitados. A tabela abaixo mapeia cada perfil da Part 14 ao seu status de implementação.

### Perfis Implementados

| Perfil | Referência Part 14 | Status | Observações |
|--------|---------------------|--------|-------------|
| **PubSub Connection** | §6.2 | ✅ Completo | Conexão com broker MQTT, roteamento por tópicos |
| **JSON NetworkMessage** | §7.2.3 | ✅ Completo | MessageType, PublisherId, DataSetWriterId, Payload com DataValue (Value + SourceTimestamp). Validado com Prosys OPC UA Browser |
| **UADP NetworkMessage** | §7.2.2 | ✅ Completo | UADPFlags, ExtendedFlags1, String PublisherId, DataSetClassId, PayloadHeader, codificação Variant com FieldCount (§7.2.2.3.3.1). Validado com OPC Labs OpcCmd |
| **DataSetMessage (KeyFrame)** | §7.2.2.3 | ✅ Completo | Mensagens KeyFrame com números de sequência. JSON e UADP |
| **Transporte MQTT** | Anexo B | ✅ Completo | QoS 0/1 sobre MQTT 3.1.1. Testado com Mosquitto e HiveMQ Cloud |
| **Múltiplos DataTypes** | Part 6 | ✅ Completo | Boolean, SByte, Byte, Int16, UInt16, Int32, UInt32, Int64, UInt64, Float, Double, String, DateTime, GUID, ByteString |
| **SecurityMode None** | §5.3.3.4 | ✅ Completo | Apropriado para redes industriais segregadas. TLS na camada de transporte MQTT disponível via configuração do broker |

### Parcialmente Implementados

| Perfil | Referência Part 14 | Status | O que Falta |
|--------|---------------------|--------|-------------|
| **DataSetMessage (Delta)** | §7.2.2.3.2 | ⚠️ Parcial | Apenas KeyFrame. Codificação DeltaFrame (somente campos alterados) não implementada. Viável — requer rastreamento de alterações por campo |
| **StatusCode no DataValue** | Part 4 | ⚠️ Parcial | Classe StatusCode existe com códigos Good/Bad/Uncertain. Ainda não transmitido em mensagens UADP. JSON inclui como parte do DataValue |
| **Papel de Subscriber** | §6.2.7 | ⚠️ Parcial | Parsing de subscriber UADP disponível (`UADPSubscriber`, `UADPNetworkMessage.decode()`), mas não integrado em API de alto nível |

### Não Implementados

| Perfil | Referência Part 14 | Viável no ESP32? | O que Seria Necessário |
|--------|---------------------|------------------|------------------------|
| **Discovery** | §6.4 | ⚠️ Limitado | |
| **MetaData Message** | §7.2.4 | ✅ Sim | DataSetMetaData (nomes de campos, tipos, descrições) como NetworkMessage separada. Adiciona ~2KB RAM. Planejado para versão futura |
| **Security Sign** | §5.3.3.4 | ❌ Não | Assinatura em nível de mensagem (SHA-256 + RSA/ECC) excede RAM do ESP32 para armazenamento de chaves e operações criptográficas. Use TLS na camada de transporte |
| **Security Sign & Encrypt** | §5.3.3.4 | ❌ Não | AES-256-GCM + troca de chaves RSA. Mesmas limitações do ESP32. TLS fornece proteção equivalente na camada de transporte |
| **Transporte UDP** | Anexo A | ❌ Não | UDP multicast requer acesso a raw sockets não disponível no stack de rede do MicroPython. Necessita módulo C ou firmware diferente |
| **Transporte AMQP** | Anexo C | ❌ Não | Biblioteca cliente AMQP 1.0 não existe para MicroPython |
| **DataSetMessage (Event)** | §7.2.2.3.4 | ✅ Sim | Mensagens tipo evento para alarmes/condições. Não priorizado — maioria dos nós sensores publica dados periódicos, não eventos |
| **WriterGroup / ReaderGroup** | §6.2.4 | ⚠️ Limitado | Objetos formais de configuração de grupo não implementados. Publicação single-writer funciona. Multi-writer necessitaria lógica de gerenciamento de grupo (~3KB RAM) |

### Validação de Interoperabilidade

| Ferramenta | Fabricante | Codificação | Transporte | Resultado |
|------------|------------|-------------|------------|-----------|
| **OPC Labs OpcCmd** | OPC Labs | UADP Binário | MQTT | ✅ 51/51 mensagens decodificadas, StatusCode Good |
| **Prosys OPC UA Browser** | Prosys OPC | JSON | MQTT | ✅ Todas as mensagens interpretadas corretamente |
| **MQTT Explorer** | Thomas Nordquist | JSON | MQTT | ✅ Estrutura validada |
| **mosquitto_sub** | Eclipse | Ambos | MQTT | ✅ Entrega de mensagens confirmada |

---

## Início Rápido

### 1. Hardware

- Placa de desenvolvimento ESP32 (qualquer variante com WiFi)
- Rede WiFi (2,4 GHz)
- Broker MQTT (Mosquitto recomendado)

### 2. Instalação

```bash
git clone https://github.com/FBR4Z/opcua_pubsub_esp32_py.git
cd opcua_pubsub_esp32_py
```

Copie os arquivos da biblioteca em `src/` para o ESP32 usando [Thonny](https://thonny.org/) ou [mpremote](https://docs.micropython.org/en/latest/reference/mpremote.html).

### 3. Configuração

Crie `config.py` no ESP32 (use `config_example.py` como template):

```python
WIFI_SSID = "sua_rede"
WIFI_PASSWORD = "sua_senha"
MQTT_BROKER = "192.168.1.100"
MQTT_PORT = 1883
```

### 4. Publicar JSON

```python
from opcua_pubsub import NetworkMessage, DataSetMessage, DataValue
from umqtt.simple import MQTTClient

mqtt = MQTTClient("ESP32", "192.168.1.100", 1883)
mqtt.connect()

nm = NetworkMessage(publisher_id="ESP32-Sensor", message_id="1")
dm = DataSetMessage(dataset_writer_id=1000, sequence_number=1)
dm.add_value("Temperature", DataValue(25.5))
dm.add_value("Pressure", DataValue(1013.25))
nm.add_dataset_message(dm)

mqtt.publish("opcua/json/data", nm.to_json())
```

### 5. Publicar UADP Binário

```python
from opcua_uadp import UADPNetworkMessage, UADPDataSetMessage, OPCUATypes

msg = UADPNetworkMessage("ESP32-Sensor")
ds = UADPDataSetMessage(dataset_writer_id=1000, sequence_number=1)
ds.add_field("Temperature", 25.5, OPCUATypes.FLOAT)
ds.add_field("Pressure", 1013.25, OPCUATypes.FLOAT)
msg.add_dataset_message(ds)

mqtt.publish("opcua/uadp/data", msg.encode())
```

---

## Estrutura do Projeto

```
opcua_pubsub_esp32_py/
├── README.md                       # Documentação em inglês
├── README_PT.md                    # Este arquivo
├── config_example.py               # Template de configuração (copie para config.py)
├── .gitignore
│
├── src/                            # Biblioteca principal
│   ├── opcua_pubsub.py             # Codificação JSON completa: NetworkMessage, DataSetMessage,
│   │                               #   DataValue com StatusCode, OPCUAPublisher (Part 14 §7.2.3)
│   ├── opcua_uadp.py               # Codificação UADP binária: UADPNetworkMessage, UADPDataSetMessage,
│   │                               #   UADPPublisher, UADPSubscriber, encoder/decoder (Part 14 §7.2.2)
│   └── opcua_micro.py              # Versão mínima: DataValue, NetworkMessage.create_json(),
│                                   #   ESPTransport — menor footprint de RAM
│
├── examples/
│   ├── main.py                     # Publisher JSON simples usando opcua_micro
│   └── lcd_display/                # Exemplo com LCD 16x2 I2C e ciclo de tipos de dados
│       ├── main.py                 # Loop principal com feedback no LCD
│       ├── boot.py                 # Inicialização WiFi com status no LCD
│       ├── lcd_i2c.py              # Driver LCD I2C (PCF8574/HD44780)
│       ├── opcua_micro.py          # Lib standalone aprimorada (adiciona metadata, auth, QoS, retain)
│       ├── config_example.py       # Template de config específico para LCD
│       ├── .gitignore              # Ignora config.py com credenciais
│       ├── README.md               # Documentação do exemplo (EN)
│       └── README_PT.md            # Documentação do exemplo (PT)
│
├── benchmarks/                     # Suite de comparação de performance
│   ├── benchmark_leve.py           # Benchmark JSON vs UADP (executa no ESP32)
│   └── echo_server.py             # Servidor echo no PC para medição de latência RTT
│
└── docs/
    └── BENCHMARK_REPORT.md         # Resultados completos de benchmark e metodologia
```

---

## Documentação

- **[docs/BENCHMARK_REPORT.md](docs/BENCHMARK_REPORT.md)** — Benchmark completo: tamanho de mensagem, throughput, latência, memória. Inclui prova de validação OpcCmd e instruções de reprodução.
- **[examples/lcd_display/README.md](examples/lcd_display/README.md)** — Guia de ligação, configuração e uso do exemplo com LCD.

---

## Aplicações Alvo

Esta implementação é otimizada para cenários específicos de IoT industrial:

| Aplicação | Adequação | Observações |
|-----------|-----------|-------------|
| Monitoramento ambiental | ✅ Excelente | Temperatura, umidade, qualidade do ar |
| Retrofit brownfield | ✅ Excelente | Adicionar conectividade a equipamentos legados |
| Prototipagem rápida | ✅ Excelente | Desenvolvimento rápido de provas de conceito |
| Rastreamento de ativos | ✅ Bom | Atualizações de localização e status |
| Manutenção preditiva | ✅ Bom | Monitoramento de vibração, corrente |
| Controle em tempo real | ❌ Não adequado | GC do MicroPython introduz jitter de 15–50 ms |

---

## Contexto da Pesquisa

Este projeto faz parte de uma **dissertação de Mestrado** em Engenharia Elétrica na **Universidade do Estado do Amazonas (UEA)**, Brasil. A pesquisa aborda a lacuna em implementações Python do OPC UA PubSub — até 2026, nenhuma outra implementação MicroPython ou Python da IEC 62541-14 existe para dispositivos com recursos limitados.

---

## Licença

Este projeto está licenciado sob a Licença MIT — veja o arquivo [LICENSE](LICENSE) para detalhes.

---

## Contato

**Fábio Braz** — Mestrando, Engenharia Elétrica, UEA

- GitHub: [@FBR4Z](https://github.com/FBR4Z)
- LinkedIn: [linkedin.com/in/fábio-braz-2b0a6ab8](https://linkedin.com/in/fábio-braz-2b0a6ab8)
- Email: eng.f.braz@gmail.com
---
