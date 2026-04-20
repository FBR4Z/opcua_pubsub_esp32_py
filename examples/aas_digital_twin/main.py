"""
Célula Robótica — ESP32 IT Publisher OPC UA PubSub
Demonstração AAS: publica dados simulados da célula robótica
usando a biblioteca opcua_pubsub.py (IEC 62541-14 JSON)

Hardware: ESP32-WROOM-32 (MicroPython)
Biblioteca: opcua_pubsub.py (src/)
Autor: Fábio Braz — Mestrado Eng. Elétrica, UEA
"""

import time
import math
import network
import machine
from umqtt.simple import MQTTClient
from opcua_pubsub import NetworkMessage, DataSetMessage, DataValue

# --- Configuração ---
try:
    from config import (
        WIFI_SSID, WIFI_PASSWORD,
        MQTT_BROKER, MQTT_PORT
    )
except ImportError:
    print("ERRO: config.py não encontrado!")
    print("Copie config_example.py para config.py e edite.")
    raise SystemExit

# --- Constantes OPC UA PubSub ---
PUBLISHER_ID = "urn:uea:celula-robotica:esp32-it"
DATASET_WRITER_ID = 2000
TOPIC = "it/opcua/celula_robotica"
PUBLISH_INTERVAL = 3  # segundos


# =============================================================================
# WiFi
# =============================================================================

def connect_wifi():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    time.sleep(1)
    
    if wlan.isconnected():
        print(f"[WiFi] Já conectado: {wlan.ifconfig()[0]}")
        return True
    
    print(f"[WiFi] Conectando a {WIFI_SSID}...", end="")
    wlan.connect(WIFI_SSID, WIFI_PASSWORD)
    
    for _ in range(20):
        if wlan.isconnected():
            print(f"\n[WiFi] OK! IP: {wlan.ifconfig()[0]}")
            return True
        print(".", end="")
        time.sleep(1)
    
    print("\n[WiFi] FALHOU!")
    return False


# =============================================================================
# Simulação da Célula Robótica
# =============================================================================

class RoboticCellSimulator:
    """
    Simula os dados de uma célula robótica:
    - Braço 4DOF: posições angulares dos 4 joints
    - Esteira: ligada/desligada
    - Sensor: peça detectada no final da esteira
    """
    
    def __init__(self):
        self.step = 0
        self.conveyor_on = True
        self.piece_detected = False
        self.cycle_count = 0
    
    def update(self):
        """Atualiza a simulação — ciclo pick-and-place."""
        self.step += 1
        t = self.step * 0.1  # tempo virtual
        
        # Ciclo da célula: a cada 10 steps muda o estado
        phase = self.step % 30
        
        if phase < 10:
            # Fase 1: Esteira rodando, peça se aproximando
            self.conveyor_on = True
            self.piece_detected = False
            # Braço em posição de espera
            j_base = 0.0
            j_shoulder = -0.5
            j_elbow = 0.3
            j_gripper = 0.0  # aberto
            
        elif phase < 15:
            # Fase 2: Peça detectada, esteira para
            self.conveyor_on = False
            self.piece_detected = True
            # Braço se move para pegar a peça
            progress = (phase - 10) / 5.0
            j_base = 0.785 * progress      # gira 45°
            j_shoulder = -0.5 + 0.3 * progress
            j_elbow = 0.3 + 0.4 * progress
            j_gripper = 0.0
            
        elif phase < 20:
            # Fase 3: Braço pegando a peça
            self.conveyor_on = False
            self.piece_detected = True
            progress = (phase - 15) / 5.0
            j_base = 0.785
            j_shoulder = -0.2
            j_elbow = 0.7
            j_gripper = 0.5 * progress  # fechando garra
            
        elif phase < 25:
            # Fase 4: Braço movendo peça para destino
            self.conveyor_on = False
            self.piece_detected = False
            progress = (phase - 20) / 5.0
            j_base = 0.785 - 1.57 * progress  # gira -90°
            j_shoulder = -0.2 - 0.3 * progress
            j_elbow = 0.7 - 0.2 * progress
            j_gripper = 0.5
            
        else:
            # Fase 5: Braço solta a peça, volta para posição inicial
            self.conveyor_on = False
            self.piece_detected = False
            progress = (phase - 25) / 5.0
            j_base = -0.785 * (1 - progress)
            j_shoulder = -0.5
            j_elbow = 0.3 + 0.2 * (1 - progress)
            j_gripper = 0.5 * (1 - progress)  # abrindo garra
            if phase == 29:
                self.cycle_count += 1
        
        # Arredonda para 3 casas decimais
        return {
            "JointBase": round(j_base, 3),
            "JointShoulder": round(j_shoulder, 3),
            "JointElbow": round(j_elbow, 3),
            "JointGripper": round(j_gripper, 3),
            "ConveyorRunning": self.conveyor_on,
            "PieceDetected": self.piece_detected,
            "CycleCount": self.cycle_count
        }


# =============================================================================
# Loop Principal
# =============================================================================

def main():
    print("\n" + "=" * 50)
    print("  CÉLULA ROBÓTICA — OPC UA PubSub Publisher")
    print("  Biblioteca: opcua_pubsub.py (IEC 62541-14)")
    print("=" * 50)
    
    # 1. Conectar WiFi
    if not connect_wifi():
        print("Reiniciando em 5s...")
        time.sleep(5)
        machine.reset()
    
    # 2. Conectar MQTT
    print(f"\n[MQTT] Conectando a {MQTT_BROKER}:{MQTT_PORT}...")
    client_id = f"esp32-it-{machine.unique_id().hex()[-6:]}"
    mqtt = MQTTClient(client_id, MQTT_BROKER, port=MQTT_PORT)
    
    try:
        mqtt.connect()
        print("[MQTT] Conectado!")
    except Exception as e:
        print(f"[MQTT] Erro: {e}")
        print("Reiniciando em 5s...")
        time.sleep(5)
        machine.reset()
    
    # 3. Iniciar simulador
    sim = RoboticCellSimulator()
    seq = 0
    
    print(f"\n[OPC UA] PublisherId: {PUBLISHER_ID}")
    print(f"[OPC UA] Tópico: {TOPIC}")
    print(f"[OPC UA] Intervalo: {PUBLISH_INTERVAL}s")
    print(f"\nPublicando...\n")
    
    # 4. Loop de publicação
    while True:
        try:
            # Atualiza simulação
            data = sim.update()
            seq += 1
            
            # Cria NetworkMessage usando a biblioteca
            nm = NetworkMessage(
                publisher_id=PUBLISHER_ID,
                message_id=str(seq)
            )
            
            dm = DataSetMessage(
                dataset_writer_id=DATASET_WRITER_ID,
                sequence_number=seq
            )
            
            # Adiciona cada campo como DataValue
            for field_name, value in data.items():
                dm.add_value(field_name, DataValue(value))
            
            nm.add_dataset_message(dm)
            
            # Publica
            json_payload = nm.to_json()
            mqtt.publish(TOPIC, json_payload)
            
            # Log compacto
            print(f"[#{seq:04d}] Base={data['JointBase']:+.3f} "
                  f"Sh={data['JointShoulder']:+.3f} "
                  f"El={data['JointElbow']:+.3f} "
                  f"Gr={data['JointGripper']:+.3f} "
                  f"Conv={'ON ' if data['ConveyorRunning'] else 'OFF'} "
                  f"Peça={'SIM' if data['PieceDetected'] else 'NÃO'} "
                  f"Ciclo={data['CycleCount']}")
            
            time.sleep(PUBLISH_INTERVAL)
            
        except OSError as e:
            print(f"\n[ERRO] Conexão perdida: {e}")
            print("Reconectando em 3s...")
            time.sleep(3)
            try:
                mqtt.connect()
                print("[MQTT] Reconectado!")
            except:
                print("[MQTT] Falha na reconexão. Reiniciando...")
                time.sleep(2)
                machine.reset()
        
        except KeyboardInterrupt:
            print("\n\nParando...")
            mqtt.disconnect()
            break


# Executa
main()
