"""
AAS Gateway — OPC UA PubSub → Asset Administration Shell
Consome mensagens OPC UA PubSub JSON da célula robótica via MQTT
e cria/atualiza um AAS usando Eclipse BaSyx Python SDK.

Requisitos:
    pip install basyx-python-sdk paho-mqtt

Autor: Fábio Braz — Mestrado Eng. Elétrica, UEA
"""

import base64
import json
import time
import urllib.error
import urllib.request
import signal
import sys
from datetime import datetime, timezone

import paho.mqtt.client as mqtt

from basyx.aas import model
from basyx.aas.adapter.aasx import AASXWriter, DictSupplementaryFileContainer
from basyx.aas.adapter.json import write_aas_json_file, AASToJsonEncoder

# =============================================================================
# Configuração
# =============================================================================

MQTT_BROKER = "127.0.0.1"   # localhost se rodar no mesmo PC que o Mosquitto
MQTT_PORT = 1883
MQTT_TOPIC = "it/opcua/celula_robotica"

AASX_OUTPUT = "celula_robotica.aasx"
AASX_INTERVAL_S = 60        # arquivo .aasx/.json (cartão SD): só de vez em quando

# Servidor AAS (Eclipse BaSyx, API AAS Part 2) — deploy/rpi5/basyx. Vazio = desligado.
BASYX_URL = "http://127.0.0.1:8081"
BASYX_INTERVAL_S = 1.0      # atualização do OperationalData no servidor
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
        description=model.MultiLanguageTextType({"en": "Base joint angle (deg)",
                                                  "pt": "Angulo do joint base (graus)"})
    ))
    sm_operational.submodel_element.add(model.Property(
        id_short="JointShoulder",
        value_type=model.datatypes.Double,
        value=0.0,
        description=model.MultiLanguageTextType({"en": "Shoulder joint angle (deg)",
                                                  "pt": "Angulo do joint ombro (graus)"})
    ))
    sm_operational.submodel_element.add(model.Property(
        id_short="JointElbow",
        value_type=model.datatypes.Double,
        value=0.0,
        description=model.MultiLanguageTextType({"en": "Elbow joint angle (deg)",
                                                  "pt": "Angulo do joint cotovelo (graus)"})
    ))
    sm_operational.submodel_element.add(model.Property(
        id_short="JointGripper",
        value_type=model.datatypes.Double,
        value=0.0,
        description=model.MultiLanguageTextType({"en": "Gripper servo angle (deg)",
                                                  "pt": "Angulo do servo da garra (graus)"})
    ))
    
    # Estado da esteira
    sm_operational.submodel_element.add(model.Property(
        id_short="ConveyorRunning",
        value_type=model.datatypes.Boolean,
        value=False,
        description=model.MultiLanguageTextType({"en": "Conveyor belt running",
                                                  "pt": "Esteira em movimento"})
    ))
    
    sm_operational.submodel_element.add(model.Property(
        id_short="ConveyorSpeed",
        value_type=model.datatypes.Int,
        value=0,
        description=model.MultiLanguageTextType({"en": "Conveyor speed (%)",
                                                  "pt": "Velocidade da esteira (%)"})
    ))

    # Sensor de peça
    sm_operational.submodel_element.add(model.Property(
        id_short="SensorDistance",
        value_type=model.datatypes.Int,
        value=None,
        description=model.MultiLanguageTextType({"en": "HC-SR04 distance (cm), empty = no reading",
                                                  "pt": "Distancia do HC-SR04 (cm), vazio = sem leitura"})
    ))
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
    
    # Fase do ciclo automático (auto_fase_t do firmware OT)
    sm_operational.submodel_element.add(model.Property(
        id_short="AutoPhase",
        value_type=model.datatypes.Int,
        value=0,
        description=model.MultiLanguageTextType({
            "en": "Auto cycle phase: 0 stopped, 1 waiting, 2 pick, 3 transport, 4 place, 5 conveyor",
            "pt": "Fase do automatico: 0 parado, 1 aguarda, 2 pega, 3 transporta, 4 solta, 5 esteira"})
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
        "ConveyorSpeed": model.datatypes.Int,
        "ConveyorRunning": model.datatypes.Boolean,
        "SensorDistance": model.datatypes.Int,
        "PieceDetected": model.datatypes.Boolean,
        "CycleCount": model.datatypes.Int,
        "AutoPhase": model.datatypes.Int,
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
            elem.value = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    
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
# Servidor AAS (API REST AAS Part 2)
# =============================================================================

def _b64url(identifier):
    """Identificadores vão na URL em base64url (AAS Part 2)."""
    return base64.urlsafe_b64encode(identifier.encode()).decode().rstrip("=")


def _http(method, url, obj=None):
    data = None if obj is None else json.dumps(obj, cls=AASToJsonEncoder).encode()
    req = urllib.request.Request(url, data=data, method=method,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=3) as resp:
        return resp.status


def basyx_upsert(obj):
    """PUT no shell/submodelo; se ainda não existir no servidor (404), POST."""
    col = "shells" if isinstance(obj, model.AssetAdministrationShell) else "submodels"
    try:
        _http("PUT", f"{BASYX_URL}/{col}/{_b64url(obj.id)}", obj)
    except urllib.error.HTTPError as e:
        if e.code != 404:
            raise
        _http("POST", f"{BASYX_URL}/{col}", obj)


# =============================================================================
# MQTT → AAS Pipeline
# =============================================================================

class AASGateway:
    def __init__(self):
        self.obj_store, self.sm_operational, self.sm_protocol = create_aas()
        self.msg_count = 0
        self.running = True
        self.t_basyx = 0.0
        self.t_aasx = time.monotonic()
        self.basyx_ok = False   # False = (re)enviar o AAS inteiro na próxima vez
        
        print("\n" + "=" * 60)
        print("  AAS GATEWAY — OPC UA PubSub → Asset Administration Shell")
        print("  Eclipse BaSyx Python SDK + Paho MQTT")
        print("=" * 60)
        print(f"\n  Broker:  {MQTT_BROKER}:{MQTT_PORT}")
        print(f"  Tópico:  {MQTT_TOPIC}")
        print(f"  Saída:   {AASX_OUTPUT} (a cada {AASX_INTERVAL_S} s)")
        print(f"  BaSyx:   {BASYX_URL or 'desligado'}")
        print()
        
        # Exporta AAS inicial (sem dados)
        export_aasx(self.obj_store, AASX_OUTPUT)
        export_json(self.obj_store, JSON_OUTPUT)
        print(f"  [AAS] Estrutura inicial criada: {AASX_OUTPUT}")
        print(f"  [AAS] JSON exportado: {JSON_OUTPUT}")
        self.sync_basyx()
        print(f"\n  Aguardando mensagens OPC UA PubSub...\n")

    def sync_basyx(self):
        """Envia o AAS ao servidor: tudo na primeira vez (ou depois de falha),
        depois só os submodelos que mudam."""
        if not BASYX_URL:
            return
        try:
            if self.basyx_ok:
                objs = [self.sm_operational, self.sm_protocol]
            else:
                objs = list(self.obj_store)
            for obj in objs:
                basyx_upsert(obj)
            if not self.basyx_ok:
                print(f"  [BaSyx] AAS publicado em {BASYX_URL}")
            self.basyx_ok = True
        except Exception as e:
            if self.basyx_ok:
                print(f"  [BaSyx] falhou ({e}); reenviando tudo na próxima")
            self.basyx_ok = False
    
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
            
            agora = time.monotonic()
            if agora - self.t_aasx >= AASX_INTERVAL_S:
                self.t_aasx = agora
                export_aasx(self.obj_store, AASX_OUTPUT)
                export_json(self.obj_store, JSON_OUTPUT)
            # Servidor e log: 1x por segundo (o gateway IT publica a 5 Hz)
            if agora - self.t_basyx < BASYX_INTERVAL_S:
                return
            self.t_basyx = agora
            self.sync_basyx()
            
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
            
            saved = " → BaSyx" if self.basyx_ok else ""
            
            print(f"  [#{self.msg_count:04d}] Seq={seq} Writer={writer_id} "
                  f"Base={jb:5.1f} Sh={js:5.1f} El={je:5.1f} Gr={jg:5.1f} "
                  f"Conv={'ON ' if conv else 'OFF'} "
                  f"Peça={'SIM' if peca else 'NÃO'} "
                  f"Ciclo={ciclo} Fase={val(payload.get('AutoPhase', 0))}{saved}")
            
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
        signal.signal(signal.SIGTERM, handle_exit)   # systemctl stop
        
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