import ujson
import utime
import urandom
from umqtt.simple import MQTTClient
import machine

# --- Core Types (Otimizados para RAM) ---
class DataValue:
    __slots__ = ('value', 'status', 'ts')
    
    def __init__(self, value, status=0, ts=None):
        self.value = value
        self.status = status
        if ts is None:
            # Timestamp simples (Unix epoch + uptime simulado)
            # Na Fase 5 adicionaremos NTP real
            self.ts = "2029-12-31T00:00:00Z" 
        else:
            self.ts = ts

    def to_dict(self):
        return {
            "Value": self.value,
            "SourceTimestamp": self.ts
        }

class NetworkMessage:
    def __init__(self, publisher_id):
        self.pub_id = publisher_id
        self.msg_id = 0
        
    def create_json(self, dataset_writer_id, seq_num, payload_dict):
        self.msg_id += 1
        
        # Converte DataValues para dicts
        processed_payload = {}
        for k, v in payload_dict.items():
            if hasattr(v, 'to_dict'):
                processed_payload[k] = v.to_dict()
            else:
                processed_payload[k] = v
                
        # Monta o dict final
        msg = {
            "MessageId": str(self.msg_id),
            "MessageType": "ua-data",
            "PublisherId": self.pub_id,
            "Messages": [{
                "DataSetWriterId": dataset_writer_id,
                "SequenceNumber": seq_num,
                "Payload": processed_payload
            }]
        }
        return ujson.dumps(msg)

# --- Camada de Transporte ---
class ESPTransport:
    def __init__(self, client_id, broker_ip):
        self.client = MQTTClient(client_id, broker_ip)
        
    def connect(self):
        print(f"Conectando ao Broker {self.client.server}...", end="")
        try:
            self.client.connect()
            print("OK")
        except OSError as e:
            print(f"Erro: {e}")
            raise e
            
    def publish(self, topic, msg_str):
        self.client.publish(topic, msg_str)