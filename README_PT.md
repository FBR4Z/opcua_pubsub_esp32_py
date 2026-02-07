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

---

## 🎯 Visão Geral

Este projeto implementa o protocolo **OPC UA PubSub** (IEC 62541-14) em **MicroPython** para microcontroladores **ESP32**. Permite que dispositivos de baixo custo participem de redes IoT industriais usando o protocolo de comunicação padrão OPC UA.

### Resultado Principal

| Métrica | Implementação C Tradicional | Esta Implementação |
|---------|------------------------------|---------------------|
| Footprint de Memória | 2-4 MB | **~30 KB** |
| Redução | - | **98,5%** |
| Custo do Hardware | €500-2000 | **€30-80** |


---

## 📊 Benchmarks de Performance

Testado em ESP32 (240MHz dual-core, MicroPython v1.27.0):

| Categoria | Métrica | Valor |
|-----------|---------|-------|
| **Memória** | Footprint da biblioteca | ~30 KB |
| **Throughput** | Taxa de publicação | 8,67 msg/s |
| **Latência** | RTT médio | 161,89 ms |
| **Jitter** | Desvio padrão RTT | 89,68 ms |
| **Confiabilidade** | Taxa de perda | **0%** |

> 📄 Relatório completo: [BENCHMARK_REPORT.md](BENCHMARK_REPORT.md)

---

## ✨ Funcionalidades

### Formatos de Codificação
- ✅ **Codificação JSON** - Legível, debugável, ampla compatibilidade
- ✅ **Codificação Binária UADP** - Compacta, eficiente para redes com banda limitada

### Transporte
- ✅ **MQTT** - Conectividade com brokers padrão (Mosquitto, HiveMQ, etc.)

### Conformidade OPC UA
- ✅ Estrutura NetworkMessage (Part 14)
- ✅ DataSetMessage com números de sequência
- ✅ DataValue com timestamps e StatusCodes
- ✅ Múltiplos tipos de dados (Boolean, Int16, UInt16, Int32, Float, Double, String, DateTime)
- ✅ Papéis de Publisher e Subscriber

---

## 🚀 Início Rápido

### 1. Requisitos de Hardware

- Placa de desenvolvimento ESP32 (qualquer variante)
- Rede WiFi (2.4 GHz)
- Broker MQTT (local ou nuvem)

### 2. Instalação

```bash
# Clone o repositório
git clone https://github.com/FBR4Z/opcua_pubsub_esp32.git
cd opcua_pubsub_esp32

# Copie os arquivos para o ESP32 usando Thonny ou mpremote
# Arquivos necessários: opcua_pubsub.py, config.py, main.py
```

### 3. Configuração

Crie `config.py` a partir do template:

```python
# WiFi
WIFI_SSID = "sua_rede"
WIFI_PASSWORD = "sua_senha"

# Broker MQTT
MQTT_BROKER = "192.168.1.100"
MQTT_PORT = 1883

# OPC UA
PUBLISHER_ID = "ESP32-OPCUA-001"
```

### 4. Executar

```python
import main
main.main()
```

---

## 📁 Estrutura do Projeto

```
opcua_pubsub_esp32/
├── opcua_pubsub.py          # Biblioteca principal (codificação JSON)
├── opcua_uadp.py            # Codificação binária UADP
├── main.py                  # Exemplo de publisher
├── subscriber_example.py    # Exemplo de subscriber
├── config.py                # Configuração (criar do template)
├── boot_wifi.py             # Helper de conexão WiFi
│
├── examples/
│   └── lcd_display/         # Exemplo com feedback LCD
│       ├── README.md
│       ├── main.py
│       ├── lcd_i2c.py
│       └── ...
│
├── benchmarks/
│   ├── benchmark_performance.py
│   ├── benchmark_json_vs_uadp.py
│   └── latency_echo_server.py
│
└── docs/
    ├── BENCHMARK_REPORT.md
    └── ROADMAP_OPC_UA_PUBSUB.md
```

---

## 💻 Exemplos de Uso

### Publisher (JSON)

```python
from opcua_pubsub import OPCUAPublisher, DataValue, StatusCode
from umqtt.simple import MQTTClient

# Configura MQTT
mqtt = MQTTClient("esp32-pub", "192.168.1.100")
publisher = OPCUAPublisher("urn:esp32:sensor", mqtt)
publisher.connect()

# Publica dados do sensor
data = {
    "Temperature": DataValue(23.5),
    "Humidity": DataValue(65.0),
    "Status": DataValue("OK")
}
publisher.publish(dataset_writer_id=1, data_dict=data)
```

### Publisher com Códigos de Qualidade

```python
from opcua_pubsub import StatusCode

# Publica com informação de qualidade explícita
data_with_quality = {
    "Temperature": (23.5, StatusCode.GOOD),
    "Pressure": (-1, StatusCode.BAD_SENSOR_FAILURE),
    "Flow": (100.5, StatusCode.UNCERTAIN)
}
publisher.publish_with_quality(1, data_with_quality)
```

### Saída da Mensagem JSON

```json
{
  "MessageId": "1",
  "MessageType": "ua-data",
  "PublisherId": "urn:esp32:sensor",
  "Messages": [{
    "DataSetWriterId": 1,
    "SequenceNumber": 1,
    "Payload": {
      "Temperature": {
        "Value": 23.5,
        "SourceTimestamp": "2024-01-15T10:30:00Z"
      },
      "Humidity": {
        "Value": 65.0,
        "SourceTimestamp": "2024-01-15T10:30:00Z"
      }
    }
  }]
}
```

---

## 🎯 Aplicações Alvo

Esta implementação é otimizada para cenários específicos de IoT industrial:

| Aplicação | Adequação | Observações |
|-----------|-----------|-------------|
| Monitoramento ambiental | ✅ Excelente | Temperatura, umidade, qualidade do ar |
| Retrofit de brownfield | ✅ Excelente | Adicionar conectividade a equipamentos legados |
| Prototipagem rápida | ✅ Excelente | Desenvolvimento rápido de provas de conceito |
| Rastreamento de ativos | ✅ Bom | Atualizações de localização e status |
| Manutenção preditiva | ✅ Bom | Monitoramento de vibração, corrente |
| Controle em tempo real | ❌ Não adequado | GC do MicroPython introduz jitter de 15-50ms |

---

## 📚 Documentação

- [Relatório de Benchmark](BENCHMARK_REPORT.md) - Análise detalhada de performance
- [Interoperabilidade UADP](UADP_INTEROPERABILIDADE_OPCMD.md) - Validação da codificação binária
- [Roadmap](ROADMAP_OPC_UA_PUBSUB.md) - Planos de desenvolvimento futuro

---

## 🔬 Contexto de Pesquisa

Este projeto faz parte de uma dissertação de Mestrado na **Universidade do Estado do Amazonas (UEA)**, Brasil, investigando a viabilidade do OPC UA PubSub em microcontroladores com recursos limitados.

### Contribuições da Pesquisa

1. **Primeira implementação em MicroPython** do OPC UA PubSub (IEC 62541-14)
2. **Redução de 98,5% na memória** comparado com implementações C tradicionais
3. **Interoperabilidade validada** com ferramentas comerciais certificadas
4. **Benchmarks abrangentes** para cenários de IoT industrial

---

## 🤝 Contribuindo

Contribuições são bem-vindas! Sinta-se à vontade para enviar um Pull Request.

### Áreas para Contribuição

- [ ] Implementação da camada de segurança (modos de segurança Part 14)
- [ ] Protocolos de transporte adicionais (UDP, AMQP)
- [ ] Mecanismos de descoberta para PubSub baseado em broker
- [ ] Suporte para outros microcontroladores (RP2040, STM32)
- [ ] Interface web de configuração

---

## 📄 Licença

Este projeto está licenciado sob a Licença MIT - veja o arquivo [LICENSE](LICENSE) para detalhes.

---

## 📧 Contato

Para perguntas sobre esta pesquisa ou oportunidades de colaboração, por favor abra uma issue ou entre em contato via LinkedIn.

---

<p align="center">
  <sub>Construído com ❤️ para a comunidade de IoT Industrial</sub>
</p>
