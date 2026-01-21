import time
import network
from opcua_micro import DataValue, NetworkMessage, ESPTransport # <--- Importa da lib!

# --- CONFIGURAÇÃO (Edite aqui) ---
SSID = "NOME_DO_SEU_WIFI"
PASSWORD = "SENHA_DO_SEU_WIFI"
BROKER_IP = "192.168.0.XX"  # <--- IP do seu Windows

def connect_wifi():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    if not wlan.isconnected():
        print('Conectando ao WiFi...')
        wlan.connect(SSID, PASSWORD)
        while not wlan.isconnected():
            time.sleep(1)
            print('.', end='')
    print('\nWiFi Conectado:', wlan.ifconfig()[0])

def main():
    print("=== MicroPython OPC UA (Library Mode) ===")
    connect_wifi()
    
    # 1. Inicializa Transporte e Mensageiro
    transport = ESPTransport("ESP32-S3-DevKit", BROKER_IP)
    nm = NetworkMessage("ESP32-S3-DevKit")
    
    try:
        transport.connect()
    except:
        print("Falha ao conectar no Broker. Verifique IP e Firewall.")
        return

    seq = 1
    while True:
        # 2. Leitura de Sensores (Simulado)
        temp_val = 25.0 + (seq % 5)
        umid_val = 60.0 + (seq % 2)
        
        # 3. Cria Payload usando classes da Lib
        payload = {
            "Temperatura": DataValue(temp_val),
            "Umidade": DataValue(umid_val)
        }
        
        # 4. Gera JSON e Envia
        json_msg = nm.create_json(dataset_writer_id=1, seq_num=seq, payload_dict=payload)
        
        transport.publish("opcua/json/esp32", json_msg)
        print(f"[Seq {seq}] Enviado: {len(json_msg)} bytes")
        
        seq += 1
        time.sleep(2)

if __name__ == "__main__":
    main()