"""
OPC UA PubSub Micro Library for ESP32
Lightweight implementation of OPC UA PubSub JSON encoding over MQTT

This library provides basic OPC UA PubSub functionality for resource-constrained
devices like ESP32, implementing the JSON encoding format as specified in
IEC 62541-14 (OPC UA Part 14: PubSub).

Author: OPC UA PubSub ESP32 Project
License: MIT
"""

import ujson
import utime
from umqtt.simple import MQTTClient


class DataValue:
    """
    OPC UA DataValue representation
    
    Encapsulates a value with optional timestamp and data type information.
    Optimized for memory efficiency using __slots__.
    """
    __slots__ = ('value', 'ts', 'data_type')
    
    def __init__(self, value, ts=None, data_type=None):
        """
        Initialize DataValue
        
        Args:
            value: The actual value (any JSON-serializable type)
            ts: Optional timestamp in ISO 8601 format
            data_type: Optional OPC UA data type name (e.g., 'Float', 'Int32')
        """
        self.value = value
        self.data_type = data_type
        if ts is None:
            # Use a default timestamp if none provided
            self.ts = "2024-01-01T00:00:00Z"
        else:
            self.ts = ts

    def to_dict(self):
        """
        Convert to dictionary for JSON serialization
        Returns simple value for compatibility with OPC UA tools
        """
        return self.value
    
    def to_full_dict(self):
        """
        Convert to full OPC UA DataValue structure
        Includes Value, SourceTimestamp, and optionally Type
        """
        result = {
            "Value": self.value,
            "SourceTimestamp": self.ts
        }
        if self.data_type:
            result["Type"] = self.data_type
        return result


class NetworkMessage:
    """
    OPC UA PubSub NetworkMessage (JSON encoding)
    
    Creates JSON-encoded NetworkMessages according to IEC 62541-14.
    Supports both simple and full message formats for compatibility
    with various OPC UA tools.
    """
    
    def __init__(self, publisher_id):
        """
        Initialize NetworkMessage
        
        Args:
            publisher_id: Unique identifier for this publisher (URN format recommended)
        """
        self.pub_id = publisher_id
        self.msg_id = 0
        
    def create_json(self, dataset_writer_id, seq_num, payload_dict):
        """
        Create a JSON-encoded NetworkMessage
        
        Args:
            dataset_writer_id: Identifier for the DataSetWriter
            seq_num: Sequence number for this message
            payload_dict: Dictionary of field_name -> DataValue pairs
            
        Returns:
            JSON string ready for MQTT publication
        """
        self.msg_id += 1
        
        # Process payload - extract simple values for broad compatibility
        processed_payload = {}
        for k, v in payload_dict.items():
            if hasattr(v, 'to_dict'):
                processed_payload[k] = v.to_dict()
            else:
                processed_payload[k] = v
                
        # Build NetworkMessage structure per IEC 62541-14
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
    
    def create_metadata_json(self, dataset_writer_id, field_definitions):
        """
        Create a DataSetMetaData message
        
        Args:
            dataset_writer_id: Identifier for the DataSetWriter
            field_definitions: Dictionary of field_name -> data_type pairs
            
        Returns:
            JSON string with metadata information
        """
        fields = []
        for name, dtype in field_definitions.items():
            fields.append({
                "Name": name,
                "DataType": dtype
            })
        
        msg = {
            "MessageId": f"meta-{dataset_writer_id}",
            "MessageType": "ua-metadata",
            "PublisherId": self.pub_id,
            "DataSetWriterId": dataset_writer_id,
            "MetaData": {
                "Fields": fields
            }
        }
        return ujson.dumps(msg)


class ESPTransport:
    """
    MQTT Transport for ESP32
    
    Handles MQTT connection and message publishing for OPC UA PubSub.
    Optimized for ESP32 with automatic reconnection support.
    """
    
    def __init__(self, client_id, broker_ip, port=1883, user=None, password=None):
        """
        Initialize MQTT transport
        
        Args:
            client_id: Unique MQTT client identifier
            broker_ip: MQTT broker IP address or hostname
            port: MQTT broker port (default 1883)
            user: Optional username for authentication
            password: Optional password for authentication
        """
        self.broker = broker_ip
        self.port = port
        self.client = MQTTClient(client_id, broker_ip, port=port,
                                  user=user, password=password)
        self.connected = False
        
    def connect(self, retry=3):
        """
        Connect to MQTT broker
        
        Args:
            retry: Number of connection attempts
            
        Returns:
            True if connected successfully, False otherwise
        """
        print(f"[MQTT] Connecting to {self.broker}:{self.port}...", end="")
        
        for attempt in range(retry):
            try:
                self.client.connect()
                self.connected = True
                print(" OK")
                return True
            except OSError as e:
                print(f" Attempt {attempt + 1} failed: {e}")
                if attempt < retry - 1:
                    utime.sleep(2)
        
        print(" FAILED")
        return False
            
    def publish(self, topic, msg_str, qos=0, retain=False):
        """
        Publish message to MQTT topic
        
        Args:
            topic: MQTT topic string
            msg_str: Message content (string)
            qos: Quality of Service level (0 or 1)
            retain: Whether to retain message on broker
            
        Returns:
            True if published successfully, False otherwise
        """
        if not self.connected:
            return False
        try:
            self.client.publish(topic, msg_str, qos=qos, retain=retain)
            return True
        except OSError as e:
            print(f"[MQTT] Publish error: {e}")
            self.connected = False
            return False
    
    def disconnect(self):
        """Disconnect from MQTT broker"""
        if self.connected:
            try:
                self.client.disconnect()
            except:
                pass
            self.connected = False
            print("[MQTT] Disconnected")
    
    def is_connected(self):
        """Check connection status"""
        return self.connected
