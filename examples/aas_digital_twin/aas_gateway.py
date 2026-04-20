"""
AAS Gateway — OPC UA PubSub → Asset Administration Shell
Consome mensagens OPC UA PubSub JSON da célula robótica via MQTT
e cria/atualiza um AAS usando Eclipse BaSyx Python SDK.

Requisitos:
    pip install basyx-python-sdk paho-mqtt

Autor: Fábio Braz — Mestrado Eng. Elétrica, UEA
"""

import json
import time
import signal
import sys
from datetime import datetime

import paho.mqtt.client as mqtt

from basyx.aas import model
from basyx.aas.adapter.aasx import AASXWriter, DictSupplementaryFileContainer
from basyx.aas.adapter.json import write_aas_json_file

# =============================================================================
# Configuração
# =============================================================================

MQTT_BROKER = "127.0.0.1"   # localhost se rodar no mesmo PC que o Mosquitto
MQTT_PORT = 1883
MQTT_TOPIC = "it/opcua/celula_robotica"

AASX_OUTPUT = "celula_robotica.aasx"
JSON_OUTPUT = "celula_robotica_aas.json"

# =============================================================================
# Criação do AAS com BaSyx Python SDK
# =============================================================================

def create_aas():
    """
    Cria a estrutura do Asset Administration Shell para a célula robótica.
    Retorna (object_store, submodel) para atualização em tempo real.
    """
    
    # --- Asset Information ---
    asset_info = model.AssetInformation(
        asset_kind=model.AssetKind.INSTANCE,
        global_asset_id="urn:uea:celula-robotica:001"
    )
    
    # --- Submodel: Nameplate (identificação do ativo) ---
    sm_nameplate = model.Submodel(
        id_="urn:uea:celula-robotica:submodel:nameplate"
    )
    sm_nameplate.id_short = "Nameplate"
    
    sm_nameplate.submodel_element.add(model.Property(
        id_short="ManufacturerName",
        value_type=model.datatypes.String,
        value="UEA — Universidade do Estado do Amazonas"
    ))
    sm_nameplate.submodel_element.add(model.Property(
        id_short="AssetType",
        value_type=model.datatypes.String,
        value="Celula Robotica 4DOF + Esteira"
    ))
    sm_nameplate.submodel_element.add(model.Property(
        id_short="CommunicationProtocol",
        value_type=model.datatypes.String,
        value="OPC UA PubSub JSON (IEC 62541-14) over MQTT"
    ))
    sm_nameplate.submodel_element.add(model.Property(
        id_short="OTITSeparation",
        value_type=model.datatypes.String,
        value="UART physical isolation (IEC 62443)"
    ))
    
    # --- Submodel: OperationalData (dados ao vivo) ---
    sm_operational = model.Submodel(
        id_="urn:uea:celula-robotica:submodel:operational-data"
    )
    sm_operational.id_short = "OperationalData"
    
    # Joints do braço robótico
    sm_operational.submodel_element.add(model.Property(
        id_short="JointBase",
        value_type=model.datatypes.Double,
        value=0.0,
        description=model.MultiLanguageTextType({"en": "Base joint angle (rad)",
                                                  "pt": "Angulo do joint base (rad)"})
    ))
    sm_operational.submodel_element.add(model.Property(
        id_short="JointShoulder",
        value_type=model.datatypes.Double,
        value=0.0,
        description=model.MultiLanguageTextType({"en": "Shoulder joint angle (rad)",
                                                  "pt": "Angulo do joint ombro (rad)"})
    ))
    sm_operational.submodel_element.add(model.Property(
        id_short="JointElbow",
        value_type=model.datatypes.Double,
        value=0.0,
        description=model.MultiLanguageTextType({"en": "Elbow joint angle (rad)",
                                                  "pt": "Angulo do joint cotovelo (rad)"})
    ))
    sm_operational.submodel_element.add(model.Property(
        id_short="JointGripper",
        value_type=model.datatypes.Double,
        value=0.0,
        description=model.MultiLanguageTextType({"en": "Gripper position (rad)",
                                                  "pt": "Posicao da garra (rad)"})
    ))
    
    # Estado da esteira
    sm_operational.submodel_element.add(model.Property(
        id_short="ConveyorRunning",
        value_type=model.datatypes.Boolean,
        value=False,
        description=model.MultiLanguageTextType({"en": "Conveyor belt running",
                                                  "pt": "Esteira em movimento"})
    ))
    
    # Sensor de peça
    sm_operational.submodel_element.add(model.Property(
        id_short="PieceDetected",
        value_type=model.datatypes.Boolean,
        value=False,
        description=model.MultiLanguageTextType({"en": "Piece detected at end of conveyor",
                                                  "pt": "Peca detectada no final da esteira"})
    ))
    
    # Contador de ciclos
    sm_operational.submodel_element.add(model.Property(
        id_short="CycleCount",
        value_type=model.datatypes.Int,
        value=0,
        description=model.MultiLanguageTextType({"en": "Pick-and-place cycle count",
                                                  "pt": "Contagem de ciclos pick-and-place"})
    ))
    
    # Timestamp da última atualização
    sm_operational.submodel_element.add(model.Property(
        id_short="LastUpdate",
        value_type=model.datatypes.String,
        value="—"
    ))
    
    # --- Submodel: OPCUAPubSubInfo (metadados do protocolo) ---
    sm_protocol = model.Submodel(
        id_="urn:uea:celula-robotica:submodel:opcua-pubsub-info"
    )
    sm_protocol.id_short = "OPCUAPubSubInfo"
    
    sm_protocol.submodel_element.add(model.Property(
        id_short="PublisherId",
        value_type=model.datatypes.String,
        value="urn:uea:celula-robotica:esp32-it"
    ))
    sm_protocol.submodel_element.add(model.Property(
        id_short="MQTTTopic",
        value_type=model.datatypes.String,
        value=MQTT_TOPIC
    ))
    sm_protocol.submodel_element.add(model.Property(
        id_short="Encoding",
        value_type=model.datatypes.String,
        value="JSON (Part 14 §7.2.3)"
    ))
    sm_protocol.submodel_element.add(model.Property(
        id_short="MessageType",
        value_type=model.datatypes.String,
        value="ua-data"
    ))
    sm_protocol.submodel_element.add(model.Property(
        id_short="DataSetWriterId",
        value_type=model.datatypes.Int,
        value=2000
    ))
    sm_protocol.submodel_element.add(model.Property(
        id_short="MessagesReceived",
        value_type=model.datatypes.Int,
        value=0
    ))
    
    # --- Asset Administration Shell ---
    aas = model.AssetAdministrationShell(
        id_="urn:uea:celula-robotica:aas:001",
        asset_information=asset_info,
        id_short="CelulaRoboticaAAS",
        submodel={
            model.ModelReference.from_referable(sm_nameplate),
            model.ModelReference.from_referable(sm_operational),
            model.ModelReference.from_referable(sm_protocol),
        }
    )
    
    # --- Object Store ---
    obj_store = model.DictObjectStore([aas, sm_nameplate, sm_operational, sm_protocol])
    
    return obj_store, sm_operational, sm_protocol


def update_submodel(sm_operational, sm_protocol, payload, msg_count):
    """
    Atualiza os valores do Submodel OperationalData com os dados
    recebidos da mensagem OPC UA PubSub.
    """
    field_map = {
        "JointBase": model.datatypes.Double,
        "JointShoulder": model.datatypes.Double,
        "JointElbow": model.datatypes.Double,
        "JointGripper": model.datatypes.Double,
        "ConveyorRunning": model.datatypes.Boolean,
        "PieceDetected": model.datatypes.Boolean,
        "CycleCount": model.datatypes.Int,
    }
    
    for elem in sm_operational.submodel_element:
        if elem.id_short in payload:
            raw = payload[elem.id_short]
            # Extrair valor: pode vir como {"Value": x, ...} ou direto
            if isinstance(raw, dict) and "Value" in raw:
                elem.value = raw["Value"]
            else:
                elem.value = raw
        elif elem.id_short == "LastUpdate":
            elem.value = datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ")
    
    # Atualiza contador no submodel de protocolo
    for elem in sm_protocol.submodel_element:
        if elem.id_short == "MessagesReceived":
            elem.value = msg_count


def export_aasx(obj_store, filepath):
    """Exporta o AAS como arquivo .aasx."""
    try:
        file_store = DictSupplementaryFileContainer()
        with AASXWriter(filepath) as writer:
            writer.write_all_aas_objects(
                "/aasx/celula_robotica.xml", obj_store, file_store
            )
        return True
    except Exception as e:
        print(f"  [AASX] Erro ao exportar: {e}")
        return False


def export_json(obj_store, filepath):
    """Exporta o AAS como JSON."""
    try:
        write_aas_json_file(filepath, obj_store)
        return True
    except Exception as e:
        print(f"  [JSON] Erro ao exportar: {e}")
        return False


# =============================================================================
# MQTT → AAS Pipeline
# =============================================================================

class AASGateway:
    def __init__(self):
        self.obj_store, self.sm_operational, self.sm_protocol = create_aas()
        self.msg_count = 0
        self.running = True
        
        print("\n" + "=" * 60)
        print("  AAS GATEWAY — OPC UA PubSub → Asset Administration Shell")
        print("  Eclipse BaSyx Python SDK + Paho MQTT")
        print("=" * 60)
        print(f"\n  Broker:  {MQTT_BROKER}:{MQTT_PORT}")
        print(f"  Tópico:  {MQTT_TOPIC}")
        print(f"  Saída:   {AASX_OUTPUT}")
        print()
        
        # Exporta AAS inicial (sem dados)
        export_aasx(self.obj_store, AASX_OUTPUT)
        export_json(self.obj_store, JSON_OUTPUT)
        print(f"  [AAS] Estrutura inicial criada: {AASX_OUTPUT}")
        print(f"  [AAS] JSON exportado: {JSON_OUTPUT}")
        print(f"\n  Aguardando mensagens OPC UA PubSub...\n")
    
    def on_connect(self, client, userdata, flags, rc, properties=None):
        if rc == 0:
            print(f"  [MQTT] Conectado ao broker!")
            client.subscribe(MQTT_TOPIC)
            print(f"  [MQTT] Subscrito em: {MQTT_TOPIC}\n")
        else:
            print(f"  [MQTT] Erro de conexão: rc={rc}")
    
    def on_message(self, client, userdata, msg):
        try:
            # Parseia a mensagem OPC UA PubSub JSON
            network_msg = json.loads(msg.payload.decode())
            
            # Valida estrutura OPC UA PubSub
            msg_type = network_msg.get("MessageType", "")
            if msg_type != "ua-data":
                return
            
            publisher_id = network_msg.get("PublisherId", "?")
            messages = network_msg.get("Messages", [])
            
            if not messages:
                return
            
            # Processa o primeiro DataSetMessage
            ds_msg = messages[0]
            seq = ds_msg.get("SequenceNumber", 0)
            writer_id = ds_msg.get("DataSetWriterId", 0)
            payload = ds_msg.get("Payload", {})
            
            self.msg_count += 1
            
            # Atualiza o AAS
            update_submodel(self.sm_operational, self.sm_protocol,
                            payload, self.msg_count)
            
            # Exporta .aasx atualizado a cada 5 mensagens (evitar I/O excessivo)
            if self.msg_count % 5 == 0 or self.msg_count <= 3:
                export_aasx(self.obj_store, AASX_OUTPUT)
                export_json(self.obj_store, JSON_OUTPUT)
            
            # Extrai valores para log
            def val(v):
                return v["Value"] if isinstance(v, dict) and "Value" in v else v
            
            jb = val(payload.get("JointBase", 0))
            js = val(payload.get("JointShoulder", 0))
            je = val(payload.get("JointElbow", 0))
            jg = val(payload.get("JointGripper", 0))
            conv = val(payload.get("ConveyorRunning", False))
            peca = val(payload.get("PieceDetected", False))
            ciclo = val(payload.get("CycleCount", 0))
            
            saved = " → .aasx" if (self.msg_count % 5 == 0 or self.msg_count <= 3) else ""
            
            print(f"  [#{self.msg_count:04d}] Seq={seq} Writer={writer_id} "
                  f"Base={jb:+.3f} Sh={js:+.3f} El={je:+.3f} Gr={jg:+.3f} "
                  f"Conv={'ON ' if conv else 'OFF'} "
                  f"Peça={'SIM' if peca else 'NÃO'} "
                  f"Ciclo={ciclo}{saved}")
            
        except json.JSONDecodeError:
            print(f"  [ERRO] JSON inválido: {msg.payload[:100]}")
        except Exception as e:
            print(f"  [ERRO] {e}")
    
    def run(self):
        client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
        client.on_connect = self.on_connect
        client.on_message = self.on_message
        
        def handle_exit(sig, frame):
            print(f"\n\n  Parando... {self.msg_count} mensagens recebidas.")
            # Exporta final
            export_aasx(self.obj_store, AASX_OUTPUT)
            export_json(self.obj_store, JSON_OUTPUT)
            print(f"  [AAS] Exportação final salva: {AASX_OUTPUT}")
            client.disconnect()
            sys.exit(0)
        
        signal.signal(signal.SIGINT, handle_exit)
        
        try:
            client.connect(MQTT_BROKER, MQTT_PORT, keepalive=60)
        except ConnectionRefusedError:
            print(f"\n  [ERRO] Não foi possível conectar ao broker {MQTT_BROKER}:{MQTT_PORT}")
            print(f"  Verifique se o Mosquitto está rodando.")
            print(f"  No PowerShell: netstat -an | findstr 1883")
            sys.exit(1)
        
        client.loop_forever()


# =============================================================================
# Main
# =============================================================================

if __name__ == "__main__":
    gateway = AASGateway()
    gateway.run()