# OPC UA PubSub MicroPython (ESP32)

> **Implementação Embarcada da Especificação OPC UA Part 14**
> **Foco:** Baixo consumo de RAM e Otimização para Microcontroladores (Edge Computing).

Esta biblioteca fornece uma implementação leve e otimizada da especificação **OPC UA Part 14 (PubSub)** escrita em MicroPython. Ela foi desenhada especificamente para rodar em dispositivos com recursos limitados (como ESP32 e RP2040), mantendo a interoperabilidade com sistemas industriais via mensagens JSON sobre MQTT.

---

## 📂 Estrutura do Projeto

```text
micropython_opcua_pubsub/
├── README.md              # Documentação Principal
├── src/
│   └── opcua_micro.py     # BIBLIOTECA: Core Logic otimizada (__slots__)
└── examples/
    ├── boot.py            # EXEMPLO: Gerenciador de conexão WiFi
    └── main.py            # EXEMPLO: Loop de leitura de sensores e publicação
📋 Status de Conformidade (Part 14)Esta implementação prioriza a eficiência de memória (RAM) em detrimento de recursos supérfluos da norma.✅ Funcionalidades ImplementadasProfile / FeatureRef. Part 14Detalhes da ImplementaçãoPubSub Base Information Model§6.2Classes otimizadas usando __slots__ para redução drástica de footprint de memória.JSON Encoding§7.2.3Serialização direta de JSON (sem overhead de objetos intermediários).Variant Data Types§6.2.2Suporte nativo para Int32, Float, String e Boolean.MQTT TransportAnexo BTransporte leve utilizando umqtt.simple (Lightweight MQTT).⚠️ Limitações de HardwareData Types: DateTime é simplificado (Unix Epoch ou String ISO básica).Security: Suporte a TLS depende da capacidade do hardware (ESP32-S3 suporta, ESP8266 não recomendado).Buffer: O tamanho das mensagens é limitado pelo buffer de transmissão do socket (tipicamente 1-4KB).🛠️ Instalação e ConfiguraçãoPré-requisitosPlaca ESP32 (S2, S3, C3 ou Clássico).Firmware MicroPython (v1.20+) instalado na placa.IDE: Thonny IDE (recomendado) ou mpremote.Passo 1: Instalar Dependências no ESP32O MicroPython precisa da biblioteca MQTT oficial. Com o ESP32 conectado ao computador e com acesso à internet (via WebREPL ou script de boot), execute no terminal do dispositivo:Pythonimport mip
mip.install("umqtt.simple")
Alternativa Offline: Copie o arquivo simple.py da biblioteca umqtt manualmente para a pasta /lib/umqtt/ do dispositivo.Passo 2: Copiar a BibliotecaCopie o arquivo src/opcua_micro.py para a raiz (ou para a pasta /lib) do seu dispositivo ESP32.Passo 3: Configurar WiFi e BrokerEdite o arquivo examples/main.py (ou boot.py dependendo da sua preferência) e insira suas credenciais:Python# Configuração de Rede
SSID = "SEU_WIFI"
PASSWORD = "SUA_SENHA"

# Configuração do Broker MQTT (IP do seu PC/Gateway)
BROKER_IP = "192.168.X.X" 
🚀 Como ExecutarOpção A: Via Thonny IDE (Desenvolvimento)Abra o arquivo examples/main.py no Thonny.Clique no botão Run (F5).Acompanhe o console:PlaintextConectando ao WiFi... OK (192.168.0.105)
Conectando ao Broker... OK
[Seq 1] Enviado: 128 bytes
Opção B: Modo Produção (Boot Automático)Para que o código rode sozinho quando você ligar o ESP32 na tomada:Salve o conteúdo de examples/boot.py como boot.py na raiz do ESP32.Salve o conteúdo de examples/main.py como main.py na raiz do ESP32.Reinicie a placa (Botão EN/RST).