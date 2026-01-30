# Exemplo OPC UA PubSub com Display LCD para ESP32

Um exemplo prático demonstrando a codificação JSON do OPC UA PubSub com feedback visual em tempo real via display LCD em microcontroladores ESP32 usando MicroPython.

![MicroPython](https://img.shields.io/badge/MicroPython-1.20+-green)
![ESP32](https://img.shields.io/badge/Plataforma-ESP32-blue)
![License](https://img.shields.io/badge/Licença-MIT-yellow)

## Visão Geral

Este exemplo demonstra como integrar o protocolo OPC UA PubSub com um display LCD 16x2 I2C, fornecendo feedback visual dos tipos de dados e valores transmitidos. Demonstra a aplicação prática de protocolos de IoT industrial em dispositivos com recursos limitados.

### Funcionalidades

- **Codificação JSON OPC UA PubSub** - Compatível com IEC 62541-14
- **Múltiplos Tipos de Dados** - Boolean, Int16, UInt16, Float, String, DateTime
- **Display LCD em Tempo Real** - Feedback visual dos valores transmitidos
- **Transporte MQTT** - Conectividade com brokers padrão
- **Reconexão WiFi Automática** - Tratamento robusto de rede
- **Baixo Consumo de Memória** - Otimizado para as restrições do ESP32

## Requisitos de Hardware

| Componente | Especificação |
|------------|---------------|
| Microcontrolador | ESP32 (qualquer variante) |
| Display | LCD 16x2 com módulo I2C (PCF8574) |
| Conexões | I2C: SDA→GPIO21, SCL→GPIO22 |

### Diagrama de Conexão

```
ESP32          Módulo LCD I2C
─────          ──────────────
3.3V    ────►  VCC
GND     ────►  GND
GPIO21  ────►  SDA
GPIO22  ────►  SCL
```

## Requisitos de Software

- MicroPython 1.20 ou posterior
- Broker MQTT (Mosquitto, HiveMQ, etc.)
- [Thonny IDE](https://thonny.org/) ou [mpremote](https://docs.micropython.org/en/latest/reference/mpremote.html)

## Instalação

### 1. Clone este repositório

```bash
git clone https://github.com/SEU_USUARIO/opcua_pubsub_esp32.git
cd opcua_pubsub_esp32/examples/lcd_display
```

### 2. Configure suas credenciais

Copie o arquivo de configuração de exemplo e edite com suas configurações:

```bash
cp config_example.py config.py
```

Edite `config.py` com suas configurações de WiFi e broker MQTT:

```python
WIFI_SSID = "sua_rede_wifi"
WIFI_PASSWORD = "sua_senha_wifi"
MQTT_BROKER = "192.168.1.100"  # IP do seu broker
```

### 3. Upload para o ESP32

Usando Thonny:
1. Abra o Thonny e conecte ao seu ESP32
2. Faça upload de todos os arquivos `.py` para a raiz do dispositivo
3. Reinicie o ESP32

Usando mpremote:
```bash
mpremote connect /dev/ttyUSB0 cp *.py :
mpremote connect /dev/ttyUSB0 reset
```

## Uso

Após o upload e reinicialização, o ESP32 irá:

1. **Fase de Boot** - Conectar ao WiFi e mostrar o endereço IP
2. **Conexão MQTT** - Conectar ao broker configurado
3. **Transmissão de Dados** - Ciclar entre diferentes tipos de dados a cada 3 segundos

### Saída do Display LCD

```
┌────────────────┐
│BOOLEAN #1      │  ← Tipo de dado e sequência
│= TRUE          │  ← Valor atual
└────────────────┘
```

### Estrutura de Tópicos MQTT

| Tópico | Descrição |
|--------|-----------|
| `opcua/lcd/data` | Mensagens de dados em tempo real |
| `opcua/lcd/metadata` | Metadados do DataSet (retido) |

### Exemplo de Mensagem JSON OPC UA

```json
{
  "MessageId": "1",
  "MessageType": "ua-data",
  "PublisherId": "urn:esp32:lcd:demo",
  "Messages": [{
    "DataSetWriterId": 1,
    "SequenceNumber": 42,
    "Payload": {
      "DataType": "Float",
      "Value": 23.45,
      "DisplayLine1": "FLOAT #42",
      "DisplayLine2": "= 23.45"
    }
  }]
}
```

## Validação com Ferramentas OPC UA

Este exemplo foi validado com:

- **Prosys OPC UA Browser** - Visualização de mensagens JSON
- **OPC Labs OpcCmd** - Teste de subscriber via linha de comando
- **MQTT Explorer** - Inspeção de mensagens raw

## Estrutura de Arquivos

```
lcd_display/
├── README.md           # Documentação em inglês
├── README_PT.md        # Este arquivo
├── config_example.py   # Template de configuração
├── boot.py             # Inicialização WiFi com feedback no LCD
├── main.py             # Loop principal da aplicação
├── opcua_micro.py      # Biblioteca OPC UA PubSub leve
├── lcd_i2c.py          # Driver LCD I2C para PCF8574
└── simple_lcd.py       # Driver LCD alternativo simplificado
```

## Solução de Problemas

### LCD não está exibindo

1. Verifique as conexões I2C (SDA, SCL)
2. Verifique o endereço I2C: endereços comuns são `0x27`, `0x3F`, `0x20`
3. Execute o scanner I2C:
   ```python
   import machine
   i2c = machine.I2C(0, scl=machine.Pin(22), sda=machine.Pin(21))
   print(i2c.scan())
   ```

### Conexão MQTT falhou

1. Verifique o endereço IP e porta do broker
2. Confirme se o broker está rodando: `mosquitto -v`
3. Teste com cliente MQTT: `mosquitto_sub -h <ip_broker> -t "opcua/#" -v`

### WiFi não conecta

1. Verifique SSID e senha no `config.py`
2. Verifique a força do sinal
3. ESP32 suporta apenas redes 2.4GHz

## Projetos Relacionados

- [opcua_pubsub_esp32](https://github.com/SEU_USUARIO/opcua_pubsub_esp32) - Biblioteca principal OPC UA PubSub para MicroPython
- [MicroPython](https://micropython.org/) - Python para microcontroladores
- [Especificação OPC UA](https://opcfoundation.org/developer-tools/specifications-unified-architecture) - Documentação oficial IEC 62541

## Contribuindo

Contribuições são bem-vindas! Sinta-se à vontade para enviar um Pull Request.

## Licença

Este projeto está licenciado sob a Licença MIT - veja o arquivo [LICENSE](../LICENSE) para detalhes.

## Autor

Desenvolvido como parte de pesquisa sobre implementação de OPC UA PubSub para dispositivos com recursos limitados.

---

*Este exemplo faz parte do projeto OPC UA PubSub ESP32, demonstrando aplicações práticas de IoT industrial com MicroPython.*
