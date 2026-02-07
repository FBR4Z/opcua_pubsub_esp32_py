"""
OPC UA PubSub Lite - MicroPython Implementation
ImplementaÃ§Ã£o do OPC UA Part 14 (PubSub) sobre MQTT para ESP32

Autor: Fabio
Projeto: DissertaÃ§Ã£o de Mestrado
"""

import ujson
import time

# =============================================================================
# StatusCode - CÃ³digos de qualidade OPC UA (Part 4)
# =============================================================================

class StatusCode:
    """CÃ³digos de status OPC UA simplificados."""
    GOOD = 0x00000000
    UNCERTAIN = 0x40000000
    BAD = 0x80000000
    BAD_SENSOR_FAILURE = 0x80B10000
    BAD_COMMUNICATION_ERROR = 0x80C00000
    BAD_OUT_OF_RANGE = 0x803C0000
    
    @staticmethod
    def is_good(code):
        return (code & 0xC0000000) == 0x00000000
    
    @staticmethod
    def is_uncertain(code):
        return (code & 0xC0000000) == 0x40000000
    
    @staticmethod
    def is_bad(code):
        return (code & 0xC0000000) == 0x80000000


# =============================================================================
# DataValue - Estrutura de valor OPC UA (Part 4)
# =============================================================================

class DataValue:
    """
    Representa um valor OPC UA com metadados.
    Baseado na estrutura DataValue do OPC UA Part 4.
    """
    
    def __init__(self, value, status_code=StatusCode.GOOD, source_timestamp=None):
        self.value = value
        self.status_code = status_code
        self.source_timestamp = source_timestamp or self._get_timestamp()
    
    def _get_timestamp(self):
        """Gera timestamp ISO 8601 UTC."""
        t = time.gmtime()
        return "{:04d}-{:02d}-{:02d}T{:02d}:{:02d}:{:02d}Z".format(
            t[0], t[1], t[2], t[3], t[4], t[5]
        )
    
    def to_dict(self):
        """Converte para dicionÃ¡rio no formato OPC UA JSON."""
        result = {
            "Value": self.value,
            "SourceTimestamp": self.source_timestamp
        }
        # SÃ³ inclui StatusCode se nÃ£o for GOOD (otimizaÃ§Ã£o)
        if self.status_code != StatusCode.GOOD:
            result["StatusCode"] = self.status_code
        return result


# =============================================================================
# DataSetMessage - Mensagem de dataset OPC UA PubSub
# =============================================================================

class DataSetMessage:
    """
    Representa uma DataSetMessage do OPC UA PubSub.
    ContÃ©m os dados de um Ãºnico DataSetWriter.
    """
    
    def __init__(self, dataset_writer_id, sequence_number=1):
        self.dataset_writer_id = dataset_writer_id
        self.sequence_number = sequence_number
        self.payload = {}
    
    def add_value(self, field_name, data_value):
        """Adiciona um DataValue ao payload."""
        if isinstance(data_value, DataValue):
            self.payload[field_name] = data_value.to_dict()
        else:
            # Se for valor simples, cria DataValue automaticamente
            self.payload[field_name] = DataValue(data_value).to_dict()
    
    def to_dict(self):
        """Converte para dicionÃ¡rio no formato OPC UA JSON."""
        return {
            "DataSetWriterId": self.dataset_writer_id,
            "SequenceNumber": self.sequence_number,
            "Payload": self.payload
        }


# =============================================================================
# NetworkMessage - Mensagem de rede OPC UA PubSub (Part 14)
# =============================================================================

class NetworkMessage:
    """
    Representa uma NetworkMessage do OPC UA PubSub Part 14.
    Este Ã© o envelope principal que contÃ©m uma ou mais DataSetMessages.
    """
    
    MESSAGE_TYPE_DATA = "ua-data"
    MESSAGE_TYPE_METADATA = "ua-metadata"
    
    def __init__(self, publisher_id, message_id=None):
        self.publisher_id = publisher_id
        self.message_id = message_id or str(time.ticks_ms())
        self.message_type = self.MESSAGE_TYPE_DATA
        self.messages = []
    
    def add_dataset_message(self, dataset_message):
        """Adiciona uma DataSetMessage Ã  NetworkMessage."""
        self.messages.append(dataset_message)
    
    def to_dict(self):
        """Converte para dicionÃ¡rio no formato OPC UA JSON (Part 14)."""
        return {
            "MessageId": self.message_id,
            "MessageType": self.message_type,
            "PublisherId": self.publisher_id,
            "Messages": [msg.to_dict() for msg in self.messages]
        }
    
    def to_json(self):
        """Serializa para JSON string."""
        return ujson.dumps(self.to_dict())


# =============================================================================
# OPCUAPublisher - Publisher principal
# =============================================================================

class OPCUAPublisher:
    """
    Publisher OPC UA PubSub sobre MQTT.
    Gerencia a conexÃ£o MQTT e publicaÃ§Ã£o de mensagens.
    """
    
    def __init__(self, publisher_id, mqtt_client, base_topic="opcua/data"):
        """
        Args:
            publisher_id: Identificador Ãºnico do publisher
            mqtt_client: InstÃ¢ncia de MQTTClient jÃ¡ configurada
            base_topic: TÃ³pico MQTT base para publicaÃ§Ã£o
        """
        self.publisher_id = publisher_id
        self.mqtt = mqtt_client
        self.base_topic = base_topic
        self.message_count = 0
        self.connected = False
    
    def connect(self):
        """Conecta ao broker MQTT."""
        try:
            self.mqtt.connect()
            self.connected = True
            print(f"[OPCUAPublisher] Conectado ao broker MQTT")
            return True
        except Exception as e:
            print(f"[OPCUAPublisher] Erro ao conectar: {e}")
            self.connected = False
            return False
    
    def disconnect(self):
        """Desconecta do broker MQTT."""
        try:
            self.mqtt.disconnect()
            self.connected = False
            print("[OPCUAPublisher] Desconectado")
        except:
            pass
    
    def publish(self, dataset_writer_id, data_dict, topic_suffix=None):
        """
        Publica dados no formato OPC UA PubSub.
        
        Args:
            dataset_writer_id: ID do DataSetWriter
            data_dict: DicionÃ¡rio {campo: valor} ou {campo: DataValue}
            topic_suffix: Sufixo opcional para o tÃ³pico
        
        Returns:
            bool: True se publicou com sucesso
        """
        if not self.connected:
            print("[OPCUAPublisher] NÃ£o conectado!")
            return False
        
        try:
            # Cria a estrutura da mensagem
            self.message_count += 1
            
            network_msg = NetworkMessage(
                publisher_id=self.publisher_id,
                message_id=str(self.message_count)
            )
            
            dataset_msg = DataSetMessage(
                dataset_writer_id=dataset_writer_id,
                sequence_number=self.message_count
            )
            
            # Adiciona os valores
            for field_name, value in data_dict.items():
                dataset_msg.add_value(field_name, value)
            
            network_msg.add_dataset_message(dataset_msg)
            
            # Serializa e publica
            json_payload = network_msg.to_json()
            
            topic = self.base_topic
            if topic_suffix:
                topic = f"{self.base_topic}/{topic_suffix}"
            
            self.mqtt.publish(topic, json_payload)
            
            print(f"[OPCUAPublisher] Publicado msg #{self.message_count} em {topic}")
            return True
            
        except Exception as e:
            print(f"[OPCUAPublisher] Erro ao publicar: {e}")
            return False
    
    def publish_with_quality(self, dataset_writer_id, data_with_quality, topic_suffix=None):
        """
        Publica dados com informaÃ§Ã£o de qualidade explÃ­cita.
        
        Args:
            dataset_writer_id: ID do DataSetWriter
            data_with_quality: Dict {campo: (valor, status_code)}
            topic_suffix: Sufixo opcional
        """
        data_dict = {}
        for field, (value, status) in data_with_quality.items():
            data_dict[field] = DataValue(value, status_code=status)
        
        return self.publish(dataset_writer_id, data_dict, topic_suffix)