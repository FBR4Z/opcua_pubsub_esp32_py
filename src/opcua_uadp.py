"""
OPC UA PubSub UADP Encoding - MicroPython Implementation
ImplementaÃ§Ã£o do OPC UA Part 14 (PubSub) com UADP Binary Encoding para ESP32

Autor: FÃ¡bio
Projeto: DissertaÃ§Ã£o de Mestrado - UEA
VersÃ£o: 1.0 - UADP Binary Encoding

ReferÃªncias:
- OPC UA Part 14: PubSub (IEC 62541-14)
- OPC UA Part 6: Mappings (Binary encoding)

Este mÃ³dulo complementa opcua_pubsub.py (JSON) com encoding binÃ¡rio UADP.
"""

import ustruct
import time

# =============================================================================
# Constantes OPC UA (Part 6 - Built-in Types)
# =============================================================================

class OPCUATypes:
    """Identificadores de tipos OPC UA Part 6."""
    BOOLEAN = 1
    SBYTE = 2
    BYTE = 3
    INT16 = 4
    UINT16 = 5
    INT32 = 6
    UINT32 = 7
    INT64 = 8
    UINT64 = 9
    FLOAT = 10
    DOUBLE = 11
    STRING = 12
    DATETIME = 13
    GUID = 14
    BYTESTRING = 15
    
    # Mapeamento Python â†’ OPC UA
    @staticmethod
    def from_python(value):
        """Infere tipo OPC UA a partir de valor Python."""
        if isinstance(value, bool):
            return OPCUATypes.BOOLEAN
        elif isinstance(value, int):
            if -128 <= value <= 127:
                return OPCUATypes.SBYTE
            elif -32768 <= value <= 32767:
                return OPCUATypes.INT16
            elif -2147483648 <= value <= 2147483647:
                return OPCUATypes.INT32
            else:
                return OPCUATypes.INT64
        elif isinstance(value, float):
            return OPCUATypes.FLOAT
        elif isinstance(value, str):
            return OPCUATypes.STRING
        elif isinstance(value, bytes):
            return OPCUATypes.BYTESTRING
        else:
            return OPCUATypes.STRING  # Fallback


# =============================================================================
# StatusCode (mesmo do JSON, para compatibilidade)
# =============================================================================

class StatusCode:
    """CÃ³digos de status OPC UA Part 4."""
    GOOD = 0x00000000
    UNCERTAIN = 0x40000000
    BAD = 0x80000000
    BAD_SENSOR_FAILURE = 0x80B10000
    BAD_COMMUNICATION_ERROR = 0x80C00000
    BAD_OUT_OF_RANGE = 0x803C0000
    
    @staticmethod
    def is_good(code):
        return (code & 0xC0000000) == 0x00000000


# =============================================================================
# UADP Network Message Flags (Part 14, Table 75)
# =============================================================================

class UADPFlags:
    """Flags para UADP NetworkMessage Header."""
    # Byte 1: UADPVersion (bits 0-3) + Flags (bits 4-7)
    VERSION_MASK = 0x0F
    PUBLISHER_ID_ENABLED = 0x10
    GROUP_HEADER_ENABLED = 0x20
    PAYLOAD_HEADER_ENABLED = 0x40
    EXTENDED_FLAGS1_ENABLED = 0x80
    
    # PublisherId Types
    PUBLISHER_ID_BYTE = 0x00
    PUBLISHER_ID_UINT16 = 0x01
    PUBLISHER_ID_UINT32 = 0x02
    PUBLISHER_ID_UINT64 = 0x03
    PUBLISHER_ID_STRING = 0x04


class UADPDataSetFlags:
    """Flags para UADP DataSetMessage Header."""
    VALID = 0x01
    FIELD_ENCODING_VARIANT = 0x00
    FIELD_ENCODING_RAWDATA = 0x01
    FIELD_ENCODING_DATAVALUE = 0x02
    SEQUENCE_NUMBER_ENABLED = 0x08
    STATUS_ENABLED = 0x10
    CONFIG_VERSION_MAJOR_ENABLED = 0x20
    CONFIG_VERSION_MINOR_ENABLED = 0x40
    FLAGS2_ENABLED = 0x80


# =============================================================================
# UADP Binary Encoder
# =============================================================================

class UADPEncoder:
    """Encoder para valores OPC UA em formato binÃ¡rio."""
    
    @staticmethod
    def encode_boolean(value):
        """Codifica Boolean (1 byte)."""
        return ustruct.pack('<B', 1 if value else 0)
    
    @staticmethod
    def encode_sbyte(value):
        """Codifica SByte (-128 a 127)."""
        return ustruct.pack('<b', value)
    
    @staticmethod
    def encode_byte(value):
        """Codifica Byte (0 a 255)."""
        return ustruct.pack('<B', value)
    
    @staticmethod
    def encode_int16(value):
        """Codifica Int16."""
        return ustruct.pack('<h', value)
    
    @staticmethod
    def encode_uint16(value):
        """Codifica UInt16."""
        return ustruct.pack('<H', value)
    
    @staticmethod
    def encode_int32(value):
        """Codifica Int32."""
        return ustruct.pack('<i', value)
    
    @staticmethod
    def encode_uint32(value):
        """Codifica UInt32."""
        return ustruct.pack('<I', value)
    
    @staticmethod
    def encode_int64(value):
        """Codifica Int64."""
        return ustruct.pack('<q', value)
    
    @staticmethod
    def encode_uint64(value):
        """Codifica UInt64."""
        return ustruct.pack('<Q', value)
    
    @staticmethod
    def encode_float(value):
        """Codifica Float (32-bit IEEE 754)."""
        return ustruct.pack('<f', value)
    
    @staticmethod
    def encode_double(value):
        """Codifica Double (64-bit IEEE 754)."""
        return ustruct.pack('<d', value)
    
    @staticmethod
    def encode_string(value):
        """Codifica String (length-prefixed UTF-8)."""
        if value is None:
            return ustruct.pack('<i', -1)  # Null string
        encoded = value.encode('utf-8')
        return ustruct.pack('<i', len(encoded)) + encoded
    
    @staticmethod
    def encode_datetime(timestamp=None):
        """
        Codifica DateTime como Windows FILETIME.
        100-nanosecond intervals since January 1, 1601.
        """
        if timestamp is None:
            # Usa tempo atual
            # MicroPython time.time() retorna segundos desde 2000-01-01
            # Precisamos converter para FILETIME
            # DiferenÃ§a 1601 â†’ 2000 = 12591158400 segundos
            EPOCH_DIFF = 12591158400 + 946684800  # 1601â†’1970 + 1970â†’2000
            try:
                secs = time.time() + 946684800  # Converte para Unix epoch
                filetime = (secs + 11644473600) * 10000000  # Para FILETIME
            except:
                filetime = 0
        else:
            filetime = timestamp
        
        return ustruct.pack('<Q', int(filetime))
    
    @staticmethod
    def encode_bytestring(value):
        """Codifica ByteString (length-prefixed bytes)."""
        if value is None:
            return ustruct.pack('<i', -1)
        return ustruct.pack('<i', len(value)) + value
    
    @staticmethod
    def encode_status_code(code):
        """Codifica StatusCode (UInt32)."""
        return ustruct.pack('<I', code)
    
    @staticmethod
    def encode_value(value, type_id=None):
        """
        Codifica valor automaticamente baseado no tipo.
        
        Args:
            value: Valor Python
            type_id: OPCUATypes (opcional, infere se nÃ£o fornecido)
        
        Returns:
            bytes: Valor codificado
        """
        if type_id is None:
            type_id = OPCUATypes.from_python(value)
        
        encoders = {
            OPCUATypes.BOOLEAN: UADPEncoder.encode_boolean,
            OPCUATypes.SBYTE: UADPEncoder.encode_sbyte,
            OPCUATypes.BYTE: UADPEncoder.encode_byte,
            OPCUATypes.INT16: UADPEncoder.encode_int16,
            OPCUATypes.UINT16: UADPEncoder.encode_uint16,
            OPCUATypes.INT32: UADPEncoder.encode_int32,
            OPCUATypes.UINT32: UADPEncoder.encode_uint32,
            OPCUATypes.INT64: UADPEncoder.encode_int64,
            OPCUATypes.UINT64: UADPEncoder.encode_uint64,
            OPCUATypes.FLOAT: UADPEncoder.encode_float,
            OPCUATypes.DOUBLE: UADPEncoder.encode_double,
            OPCUATypes.STRING: UADPEncoder.encode_string,
            OPCUATypes.DATETIME: UADPEncoder.encode_datetime,
            OPCUATypes.BYTESTRING: UADPEncoder.encode_bytestring,
        }
        
        encoder = encoders.get(type_id)
        if encoder:
            return encoder(value)
        else:
            # Fallback: tenta como string
            return UADPEncoder.encode_string(str(value))


# =============================================================================
# UADP Binary Decoder
# =============================================================================

class UADPDecoder:
    """Decoder para valores OPC UA em formato binÃ¡rio."""
    
    @staticmethod
    def decode_boolean(data, offset=0):
        """Decodifica Boolean."""
        value = ustruct.unpack_from('<B', data, offset)[0]
        return (value != 0, offset + 1)
    
    @staticmethod
    def decode_sbyte(data, offset=0):
        """Decodifica SByte."""
        value = ustruct.unpack_from('<b', data, offset)[0]
        return (value, offset + 1)
    
    @staticmethod
    def decode_byte(data, offset=0):
        """Decodifica Byte."""
        value = ustruct.unpack_from('<B', data, offset)[0]
        return (value, offset + 1)
    
    @staticmethod
    def decode_int16(data, offset=0):
        """Decodifica Int16."""
        value = ustruct.unpack_from('<h', data, offset)[0]
        return (value, offset + 2)
    
    @staticmethod
    def decode_uint16(data, offset=0):
        """Decodifica UInt16."""
        value = ustruct.unpack_from('<H', data, offset)[0]
        return (value, offset + 2)
    
    @staticmethod
    def decode_int32(data, offset=0):
        """Decodifica Int32."""
        value = ustruct.unpack_from('<i', data, offset)[0]
        return (value, offset + 4)
    
    @staticmethod
    def decode_uint32(data, offset=0):
        """Decodifica UInt32."""
        value = ustruct.unpack_from('<I', data, offset)[0]
        return (value, offset + 4)
    
    @staticmethod
    def decode_int64(data, offset=0):
        """Decodifica Int64."""
        value = ustruct.unpack_from('<q', data, offset)[0]
        return (value, offset + 8)
    
    @staticmethod
    def decode_uint64(data, offset=0):
        """Decodifica UInt64."""
        value = ustruct.unpack_from('<Q', data, offset)[0]
        return (value, offset + 8)
    
    @staticmethod
    def decode_float(data, offset=0):
        """Decodifica Float."""
        value = ustruct.unpack_from('<f', data, offset)[0]
        return (value, offset + 4)
    
    @staticmethod
    def decode_double(data, offset=0):
        """Decodifica Double."""
        value = ustruct.unpack_from('<d', data, offset)[0]
        return (value, offset + 8)
    
    @staticmethod
    def decode_string(data, offset=0):
        """Decodifica String."""
        length = ustruct.unpack_from('<i', data, offset)[0]
        offset += 4
        if length < 0:
            return (None, offset)
        value = data[offset:offset + length].decode('utf-8')
        return (value, offset + length)
    
    @staticmethod
    def decode_datetime(data, offset=0):
        """Decodifica DateTime (FILETIME)."""
        filetime = ustruct.unpack_from('<Q', data, offset)[0]
        return (filetime, offset + 8)
    
    @staticmethod
    def decode_bytestring(data, offset=0):
        """Decodifica ByteString."""
        length = ustruct.unpack_from('<i', data, offset)[0]
        offset += 4
        if length < 0:
            return (None, offset)
        value = data[offset:offset + length]
        return (value, offset + length)
    
    @staticmethod
    def decode_value(data, type_id, offset=0):
        """Decodifica valor baseado no tipo."""
        decoders = {
            OPCUATypes.BOOLEAN: UADPDecoder.decode_boolean,
            OPCUATypes.SBYTE: UADPDecoder.decode_sbyte,
            OPCUATypes.BYTE: UADPDecoder.decode_byte,
            OPCUATypes.INT16: UADPDecoder.decode_int16,
            OPCUATypes.UINT16: UADPDecoder.decode_uint16,
            OPCUATypes.INT32: UADPDecoder.decode_int32,
            OPCUATypes.UINT32: UADPDecoder.decode_uint32,
            OPCUATypes.INT64: UADPDecoder.decode_int64,
            OPCUATypes.UINT64: UADPDecoder.decode_uint64,
            OPCUATypes.FLOAT: UADPDecoder.decode_float,
            OPCUATypes.DOUBLE: UADPDecoder.decode_double,
            OPCUATypes.STRING: UADPDecoder.decode_string,
            OPCUATypes.DATETIME: UADPDecoder.decode_datetime,
            OPCUATypes.BYTESTRING: UADPDecoder.decode_bytestring,
        }
        
        decoder = decoders.get(type_id)
        if decoder:
            return decoder(data, offset)
        else:
            raise ValueError(f"Tipo nÃ£o suportado: {type_id}")


# =============================================================================
# UADP DataValue (com metadados)
# =============================================================================

class UADPDataValue:
    """
    DataValue UADP com valor, status e timestamp.
    Formato mais compacto que JSON.
    """
    
    def __init__(self, value, type_id=None, status_code=StatusCode.GOOD, 
                 source_timestamp=None):
        self.value = value
        self.type_id = type_id or OPCUATypes.from_python(value)
        self.status_code = status_code
        self.source_timestamp = source_timestamp
    
    def encode(self, include_status=False, include_timestamp=False):
        """
        Codifica DataValue.
        
        Args:
            include_status: Incluir StatusCode (4 bytes extra)
            include_timestamp: Incluir SourceTimestamp (8 bytes extra)
        """
        buffer = bytearray()
        
        # Encoding mask (1 byte)
        mask = 0x01  # Value present
        if include_status and self.status_code != StatusCode.GOOD:
            mask |= 0x02
        if include_timestamp:
            mask |= 0x04
        buffer.append(mask)
        
        # Value
        buffer.extend(UADPEncoder.encode_value(self.value, self.type_id))
        
        # StatusCode (opcional)
        if mask & 0x02:
            buffer.extend(UADPEncoder.encode_status_code(self.status_code))
        
        # SourceTimestamp (opcional)
        if mask & 0x04:
            buffer.extend(UADPEncoder.encode_datetime(self.source_timestamp))
        
        return bytes(buffer)
    
    def encode_raw(self):
        """Codifica apenas o valor (sem metadados) - mais compacto."""
        return UADPEncoder.encode_value(self.value, self.type_id)
    
    @staticmethod
    def decode(data, type_id, offset=0):
        """Decodifica DataValue."""
        mask = data[offset]
        offset += 1
        
        value = None
        status_code = StatusCode.GOOD
        timestamp = None
        
        if mask & 0x01:
            value, offset = UADPDecoder.decode_value(data, type_id, offset)
        
        if mask & 0x02:
            status_code, offset = UADPDecoder.decode_uint32(data, offset)
        
        if mask & 0x04:
            timestamp, offset = UADPDecoder.decode_datetime(data, offset)
        
        return (UADPDataValue(value, type_id, status_code, timestamp), offset)


# =============================================================================
# UADP DataSetMessage
# =============================================================================

class UADPDataSetMessage:
    """
    DataSetMessage em formato UADP binÃ¡rio.
    ContÃ©m campos de um DataSet.
    """
    
    def __init__(self, dataset_writer_id, sequence_number=0):
        self.dataset_writer_id = dataset_writer_id
        self.sequence_number = sequence_number
        self.fields = []  # Lista de (nome, valor, tipo)
        self.field_encoding = UADPDataSetFlags.FIELD_ENCODING_RAWDATA
        self.status = StatusCode.GOOD
    
    def add_field(self, name, value, type_id=None):
        """
        Adiciona campo ao DataSet.
        
        Args:
            name: Nome do campo (para referÃªncia, nÃ£o codificado em RawData)
            value: Valor do campo
            type_id: Tipo OPC UA (opcional, infere automaticamente)
        """
        if type_id is None:
            type_id = OPCUATypes.from_python(value)
        self.fields.append((name, value, type_id))
    
    def add_data_value(self, name, data_value):
        """Adiciona UADPDataValue."""
        self.fields.append((name, data_value.value, data_value.type_id))
    
    def encode(self):
        """
        Codifica DataSetMessage em UADP.
        Usa RawData encoding (mais compacto).
        """
        buffer = bytearray()
        
        # DataSetMessage Header
        # Flags1 (1 byte)
        flags1 = UADPDataSetFlags.VALID
        flags1 |= (self.field_encoding << 1)
        flags1 |= UADPDataSetFlags.SEQUENCE_NUMBER_ENABLED
        buffer.append(flags1)
        
        # Flags2 (1 byte) - simplificado
        flags2 = 0x00  # Nenhum campo extra
        buffer.append(flags2)
        
        # SequenceNumber (2 bytes)
        buffer.extend(ustruct.pack('<H', self.sequence_number & 0xFFFF))
        
        # Payload: RawData encoding
        # Cada campo Ã© codificado diretamente, sem tipo (subscriber precisa conhecer schema)
        for name, value, type_id in self.fields:
            buffer.extend(UADPEncoder.encode_value(value, type_id))
        
        return bytes(buffer)
    
    def encode_with_types(self):
        """
        Codifica com informaÃ§Ã£o de tipos (Variant encoding).
        Maior mas auto-descritivo.
        """
        buffer = bytearray()
        
        # Flags1
        flags1 = UADPDataSetFlags.VALID
        flags1 |= (UADPDataSetFlags.FIELD_ENCODING_VARIANT << 1)
        flags1 |= UADPDataSetFlags.SEQUENCE_NUMBER_ENABLED
        buffer.append(flags1)
        
        # Flags2
        buffer.append(0x00)
        
        # SequenceNumber
        buffer.extend(ustruct.pack('<H', self.sequence_number & 0xFFFF))
        
        # Field count
        buffer.extend(ustruct.pack('<H', len(self.fields)))
        
        # Cada campo como Variant (TypeId + Value)
        for name, value, type_id in self.fields:
            buffer.append(type_id)  # TypeId (1 byte)
            buffer.extend(UADPEncoder.encode_value(value, type_id))
        
        return bytes(buffer)
    
    def get_field_names(self):
        """Retorna lista de nomes de campos."""
        return [f[0] for f in self.fields]
    
    def get_field(self, name):
        """Retorna valor de um campo por nome."""
        for fname, value, type_id in self.fields:
            if fname == name:
                return value
        return None


# =============================================================================
# UADP NetworkMessage
# =============================================================================

class UADPNetworkMessage:
    """
    NetworkMessage em formato UADP binÃ¡rio.
    Envelope principal contendo DataSetMessages.
    """
    
    VERSION = 1
    
    def __init__(self, publisher_id, writer_group_id=1):
        self.publisher_id = publisher_id
        self.writer_group_id = writer_group_id
        self.dataset_messages = []
        self.sequence_number = 0
        self.timestamp = None
        
        # ConfiguraÃ§Ãµes de encoding
        self.include_group_header = True
        self.include_payload_header = True
        self.publisher_id_type = UADPFlags.PUBLISHER_ID_STRING
    
    def add_dataset_message(self, dataset_msg):
        """Adiciona DataSetMessage."""
        self.dataset_messages.append(dataset_msg)
    
    def encode(self):
        """
        Codifica NetworkMessage completa em UADP.
        
        Returns:
            bytes: Mensagem UADP binÃ¡ria
        """
        buffer = bytearray()
        
        # ===== 1. NetworkMessage Header =====
        
        # Byte 1: Version + Flags
        flags = self.VERSION & UADPFlags.VERSION_MASK
        flags |= UADPFlags.PUBLISHER_ID_ENABLED
        if self.include_group_header:
            flags |= UADPFlags.GROUP_HEADER_ENABLED
        if self.include_payload_header:
            flags |= UADPFlags.PAYLOAD_HEADER_ENABLED
        buffer.append(flags)
        
        # Extended Flags (nÃ£o usado nesta versÃ£o simplificada)
        
        # PublisherId
        if isinstance(self.publisher_id, str):
            # String PublisherId
            buffer.append(UADPFlags.PUBLISHER_ID_STRING)
            buffer.extend(UADPEncoder.encode_string(self.publisher_id))
        elif isinstance(self.publisher_id, int):
            if self.publisher_id <= 255:
                buffer.append(UADPFlags.PUBLISHER_ID_BYTE)
                buffer.append(self.publisher_id)
            elif self.publisher_id <= 65535:
                buffer.append(UADPFlags.PUBLISHER_ID_UINT16)
                buffer.extend(ustruct.pack('<H', self.publisher_id))
            else:
                buffer.append(UADPFlags.PUBLISHER_ID_UINT32)
                buffer.extend(ustruct.pack('<I', self.publisher_id))
        
        # ===== 2. Group Header (opcional) =====
        if self.include_group_header:
            # GroupFlags (1 byte)
            group_flags = 0x03  # WriterGroupId + GroupVersion enabled
            buffer.append(group_flags)
            
            # WriterGroupId (2 bytes)
            buffer.extend(ustruct.pack('<H', self.writer_group_id))
            
            # GroupVersion (4 bytes) - usando 0 para simplicidade
            buffer.extend(ustruct.pack('<I', 0))
            
            # NetworkMessageNumber (2 bytes)
            buffer.extend(ustruct.pack('<H', self.sequence_number & 0xFFFF))
        
        # ===== 3. Payload Header =====
        if self.include_payload_header:
            # Count of DataSetMessages (1 byte)
            buffer.append(len(self.dataset_messages))
            
            # DataSetWriterIds (2 bytes cada)
            for ds_msg in self.dataset_messages:
                buffer.extend(ustruct.pack('<H', ds_msg.dataset_writer_id))
        
        # ===== 4. Payload: DataSetMessages =====
        if len(self.dataset_messages) > 1:
            # Multiple messages: precisa de sizes
            encoded_messages = [msg.encode() for msg in self.dataset_messages]
            
            # Sizes (2 bytes cada)
            for enc_msg in encoded_messages:
                buffer.extend(ustruct.pack('<H', len(enc_msg)))
            
            # Messages
            for enc_msg in encoded_messages:
                buffer.extend(enc_msg)
        else:
            # Single message: direto
            for ds_msg in self.dataset_messages:
                buffer.extend(ds_msg.encode())
        
        return bytes(buffer)
    
    def encode_minimal(self):
        """
        Encoding mÃ­nimo para mÃ¡xima eficiÃªncia.
        Remove headers opcionais.
        """
        buffer = bytearray()
        
        # Flags mÃ­nimas
        flags = self.VERSION | UADPFlags.PUBLISHER_ID_ENABLED
        buffer.append(flags)
        
        # PublisherId como byte se possÃ­vel
        if isinstance(self.publisher_id, int) and self.publisher_id <= 255:
            buffer.append(UADPFlags.PUBLISHER_ID_BYTE)
            buffer.append(self.publisher_id)
        else:
            buffer.append(UADPFlags.PUBLISHER_ID_STRING)
            pub_bytes = str(self.publisher_id).encode('utf-8')[:16]  # Max 16 chars
            buffer.extend(ustruct.pack('<i', len(pub_bytes)))
            buffer.extend(pub_bytes)
        
        # DataSetMessage count
        buffer.append(len(self.dataset_messages))
        
        # DataSetMessages direto
        for ds_msg in self.dataset_messages:
            buffer.extend(ds_msg.encode())
        
        return bytes(buffer)
    
    @staticmethod
    def decode(data):
        """
        Decodifica NetworkMessage UADP.
        
        Args:
            data: bytes da mensagem
        
        Returns:
            UADPNetworkMessage ou None se invÃ¡lido
        """
        if len(data) < 2:
            return None
        
        offset = 0
        msg = UADPNetworkMessage("", 0)
        
        # Flags
        flags = data[offset]
        offset += 1
        
        version = flags & UADPFlags.VERSION_MASK
        if version != 1:
            print(f"[UADP] VersÃ£o nÃ£o suportada: {version}")
            return None
        
        has_publisher_id = flags & UADPFlags.PUBLISHER_ID_ENABLED
        has_group_header = flags & UADPFlags.GROUP_HEADER_ENABLED
        has_payload_header = flags & UADPFlags.PAYLOAD_HEADER_ENABLED
        
        # PublisherId
        if has_publisher_id:
            pub_type = data[offset]
            offset += 1
            
            if pub_type == UADPFlags.PUBLISHER_ID_BYTE:
                msg.publisher_id = data[offset]
                offset += 1
            elif pub_type == UADPFlags.PUBLISHER_ID_UINT16:
                msg.publisher_id = ustruct.unpack_from('<H', data, offset)[0]
                offset += 2
            elif pub_type == UADPFlags.PUBLISHER_ID_UINT32:
                msg.publisher_id = ustruct.unpack_from('<I', data, offset)[0]
                offset += 4
            elif pub_type == UADPFlags.PUBLISHER_ID_STRING:
                msg.publisher_id, offset = UADPDecoder.decode_string(data, offset)
        
        # Group Header
        if has_group_header:
            group_flags = data[offset]
            offset += 1
            
            if group_flags & 0x01:  # WriterGroupId
                msg.writer_group_id = ustruct.unpack_from('<H', data, offset)[0]
                offset += 2
            
            if group_flags & 0x02:  # GroupVersion
                offset += 4  # Skip
            
            if group_flags & 0x04:  # NetworkMessageNumber
                msg.sequence_number = ustruct.unpack_from('<H', data, offset)[0]
                offset += 2
        
        # Payload Header
        ds_count = 1
        writer_ids = []
        
        if has_payload_header:
            ds_count = data[offset]
            offset += 1
            
            for _ in range(ds_count):
                wid = ustruct.unpack_from('<H', data, offset)[0]
                writer_ids.append(wid)
                offset += 2
        
        # Nota: DecodificaÃ§Ã£o completa de DataSetMessages requer
        # conhecimento do schema (tipos dos campos)
        # Por enquanto, armazenamos os bytes restantes
        msg._raw_payload = data[offset:]
        msg._writer_ids = writer_ids
        msg._ds_count = ds_count
        
        return msg


# =============================================================================
# UADP Publisher
# =============================================================================

class UADPPublisher:
    """
    Publisher OPC UA PubSub com UADP encoding sobre MQTT.
    Interface similar ao OPCUAPublisher (JSON) para fÃ¡cil migraÃ§Ã£o.
    """
    
    def __init__(self, publisher_id, mqtt_client, base_topic="opcua/uadp"):
        """
        Args:
            publisher_id: Identificador do publisher (string ou int)
            mqtt_client: InstÃ¢ncia MQTTClient configurada
            base_topic: TÃ³pico MQTT base
        """
        self.publisher_id = publisher_id
        self.mqtt = mqtt_client
        self.base_topic = base_topic
        self.message_count = 0
        self.connected = False
        self.writer_group_id = 1
        
        # EstatÃ­sticas
        self.bytes_sent = 0
    
    def connect(self):
        """Conecta ao broker MQTT."""
        try:
            self.mqtt.connect()
            self.connected = True
            print(f"[UADPPublisher] Conectado ao broker MQTT")
            return True
        except Exception as e:
            print(f"[UADPPublisher] Erro ao conectar: {e}")
            self.connected = False
            return False
    
    def disconnect(self):
        """Desconecta do broker."""
        try:
            self.mqtt.disconnect()
            self.connected = False
            print("[UADPPublisher] Desconectado")
        except:
            pass
    
    def publish(self, dataset_writer_id, data_dict, topic_suffix=None):
        """
        Publica dados em formato UADP.
        
        Args:
            dataset_writer_id: ID do DataSetWriter
            data_dict: Dict {campo: valor} ou {campo: (valor, tipo)}
            topic_suffix: Sufixo opcional para tÃ³pico
        
        Returns:
            bool: True se publicou com sucesso
        """
        if not self.connected:
            print("[UADPPublisher] NÃ£o conectado!")
            return False
        
        try:
            self.message_count += 1
            
            # Cria NetworkMessage
            net_msg = UADPNetworkMessage(
                publisher_id=self.publisher_id,
                writer_group_id=self.writer_group_id
            )
            net_msg.sequence_number = self.message_count
            
            # Cria DataSetMessage
            ds_msg = UADPDataSetMessage(
                dataset_writer_id=dataset_writer_id,
                sequence_number=self.message_count
            )
            
            # Adiciona campos
            for field_name, value in data_dict.items():
                if isinstance(value, tuple):
                    # (valor, tipo) explÃ­cito
                    ds_msg.add_field(field_name, value[0], value[1])
                elif isinstance(value, UADPDataValue):
                    ds_msg.add_data_value(field_name, value)
                else:
                    # Infere tipo
                    ds_msg.add_field(field_name, value)
            
            net_msg.add_dataset_message(ds_msg)
            
            # Serializa
            payload = net_msg.encode()
            
            # Publica
            topic = self.base_topic
            if topic_suffix:
                topic = f"{self.base_topic}/{topic_suffix}"
            
            self.mqtt.publish(topic, payload)
            self.bytes_sent += len(payload)
            
            print(f"[UADPPublisher] Msg #{self.message_count}: {len(payload)} bytes em {topic}")
            return True
            
        except Exception as e:
            print(f"[UADPPublisher] Erro: {e}")
            return False
    
    def publish_minimal(self, dataset_writer_id, data_dict, topic_suffix=None):
        """
        Publica com encoding mÃ­nimo para mÃ¡xima eficiÃªncia.
        """
        if not self.connected:
            return False
        
        try:
            self.message_count += 1
            
            net_msg = UADPNetworkMessage(self.publisher_id, self.writer_group_id)
            net_msg.sequence_number = self.message_count
            
            ds_msg = UADPDataSetMessage(dataset_writer_id, self.message_count)
            
            for field_name, value in data_dict.items():
                if isinstance(value, tuple):
                    ds_msg.add_field(field_name, value[0], value[1])
                else:
                    ds_msg.add_field(field_name, value)
            
            net_msg.add_dataset_message(ds_msg)
            
            # Usa encoding mÃ­nimo
            payload = net_msg.encode_minimal()
            
            topic = self.base_topic
            if topic_suffix:
                topic = f"{self.base_topic}/{topic_suffix}"
            
            self.mqtt.publish(topic, payload)
            self.bytes_sent += len(payload)
            
            return True
            
        except Exception as e:
            print(f"[UADPPublisher] Erro: {e}")
            return False
    
    def get_stats(self):
        """Retorna estatÃ­sticas."""
        return {
            "messages_sent": self.message_count,
            "bytes_sent": self.bytes_sent,
            "avg_msg_size": self.bytes_sent / max(self.message_count, 1)
        }


# =============================================================================
# UADP Subscriber
# =============================================================================

class UADPSubscriber:
    """
    Subscriber OPC UA PubSub para mensagens UADP.
    """
    
    def __init__(self, subscriber_id, mqtt_client):
        self.subscriber_id = subscriber_id
        self.mqtt = mqtt_client
        self.connected = False
        self.subscriptions = []
        
        # Callbacks
        self._on_message_callback = None
        self._on_raw_callback = None
        self._on_error_callback = None
        
        # EstatÃ­sticas
        self.stats = {
            "received": 0,
            "decoded": 0,
            "errors": 0,
            "bytes_received": 0
        }
    
    def connect(self):
        """Conecta ao broker."""
        try:
            self.mqtt.connect()
            self.mqtt.set_callback(self._mqtt_callback)
            self.connected = True
            print(f"[UADPSubscriber] Conectado")
            return True
        except Exception as e:
            print(f"[UADPSubscriber] Erro: {e}")
            return False
    
    def disconnect(self):
        """Desconecta."""
        try:
            self.mqtt.disconnect()
            self.connected = False
            print("[UADPSubscriber] Desconectado")
        except:
            pass
    
    def subscribe(self, topic="opcua/uadp/#"):
        """Inscreve em tÃ³pico."""
        if not self.connected:
            return False
        
        try:
            self.mqtt.subscribe(topic)
            self.subscriptions.append(topic)
            print(f"[UADPSubscriber] Inscrito em: {topic}")
            return True
        except Exception as e:
            print(f"[UADPSubscriber] Erro: {e}")
            return False
    
    def on_message(self, callback):
        """
        Define callback para mensagens decodificadas.
        callback(network_message: UADPNetworkMessage, topic: str)
        """
        self._on_message_callback = callback
    
    def on_raw(self, callback):
        """
        Define callback para dados brutos.
        callback(topic: str, payload: bytes)
        """
        self._on_raw_callback = callback
    
    def on_error(self, callback):
        """
        Define callback para erros.
        callback(error: str, payload: bytes)
        """
        self._on_error_callback = callback
    
    def _mqtt_callback(self, topic, payload):
        """Callback interno MQTT."""
        self.stats["received"] += 1
        self.stats["bytes_received"] += len(payload)
        
        if isinstance(topic, bytes):
            topic = topic.decode()
        
        # Callback raw
        if self._on_raw_callback:
            self._on_raw_callback(topic, payload)
        
        # Tenta decodificar
        try:
            net_msg = UADPNetworkMessage.decode(payload)
            
            if net_msg:
                self.stats["decoded"] += 1
                
                if self._on_message_callback:
                    self._on_message_callback(net_msg, topic)
            else:
                self.stats["errors"] += 1
                if self._on_error_callback:
                    self._on_error_callback("Falha ao decodificar", payload)
                    
        except Exception as e:
            self.stats["errors"] += 1
            if self._on_error_callback:
                self._on_error_callback(str(e), payload)
    
    def check_messages(self):
        """Verifica mensagens pendentes (nÃ£o-bloqueante)."""
        if not self.connected:
            return
        try:
            self.mqtt.check_msg()
        except:
            pass
    
    def wait_message(self):
        """Aguarda prÃ³xima mensagem (bloqueante)."""
        if not self.connected:
            return
        try:
            self.mqtt.wait_msg()
        except:
            pass
    
    def get_stats(self):
        """Retorna estatÃ­sticas."""
        return self.stats.copy()


# =============================================================================
# FunÃ§Ãµes UtilitÃ¡rias
# =============================================================================

def compare_encoding_size(data_dict):
    """
    Compara tamanho entre JSON e UADP para mesmo payload.
    
    Args:
        data_dict: Dict {campo: valor}
    
    Returns:
        dict com tamanhos e economia
    """
    import ujson
    
    # Simula JSON (usando estrutura do opcua_pubsub.py)
    json_msg = {
        "MessageId": "1",
        "MessageType": "ua-data",
        "PublisherId": "ESP32",
        "Messages": [{
            "DataSetWriterId": 1000,
            "SequenceNumber": 1,
            "Payload": {}
        }]
    }
    
    for field, value in data_dict.items():
        json_msg["Messages"][0]["Payload"][field] = {
            "Value": value,
            "SourceTimestamp": "2026-01-11T00:00:00Z"
        }
    
    json_bytes = len(ujson.dumps(json_msg))
    
    # UADP
    net_msg = UADPNetworkMessage("ESP32", 1)
    ds_msg = UADPDataSetMessage(1000, 1)
    for field, value in data_dict.items():
        ds_msg.add_field(field, value)
    net_msg.add_dataset_message(ds_msg)
    
    uadp_bytes = len(net_msg.encode())
    uadp_minimal = len(net_msg.encode_minimal())
    
    savings_pct = (1 - uadp_bytes / json_bytes) * 100
    savings_minimal_pct = (1 - uadp_minimal / json_bytes) * 100
    
    return {
        "json_bytes": json_bytes,
        "uadp_bytes": uadp_bytes,
        "uadp_minimal_bytes": uadp_minimal,
        "savings_percent": round(savings_pct, 1),
        "savings_minimal_percent": round(savings_minimal_pct, 1),
        "ratio": round(json_bytes / uadp_bytes, 2)
    }


def benchmark_encoding(num_iterations=100, num_fields=5):
    """
    Benchmark de performance: JSON vs UADP.
    
    Returns:
        dict com tempos de serializaÃ§Ã£o
    """
    import ujson
    
    # Dados de teste
    data = {f"Field_{i}": i * 10.5 for i in range(num_fields)}
    
    # Benchmark JSON
    json_times = []
    for i in range(num_iterations):
        t0 = time.ticks_us()
        
        json_msg = {
            "MessageId": str(i),
            "MessageType": "ua-data",
            "PublisherId": "ESP32",
            "Messages": [{
                "DataSetWriterId": 1000,
                "SequenceNumber": i,
                "Payload": {f: {"Value": v} for f, v in data.items()}
            }]
        }
        _ = ujson.dumps(json_msg)
        
        t1 = time.ticks_us()
        json_times.append(time.ticks_diff(t1, t0))
    
    # Benchmark UADP
    uadp_times = []
    for i in range(num_iterations):
        t0 = time.ticks_us()
        
        net_msg = UADPNetworkMessage("ESP32", 1)
        net_msg.sequence_number = i
        ds_msg = UADPDataSetMessage(1000, i)
        for f, v in data.items():
            ds_msg.add_field(f, v)
        net_msg.add_dataset_message(ds_msg)
        _ = net_msg.encode()
        
        t1 = time.ticks_us()
        uadp_times.append(time.ticks_diff(t1, t0))
    
    # Benchmark UADP Minimal
    uadp_min_times = []
    for i in range(num_iterations):
        t0 = time.ticks_us()
        
        net_msg = UADPNetworkMessage("ESP32", 1)
        net_msg.sequence_number = i
        ds_msg = UADPDataSetMessage(1000, i)
        for f, v in data.items():
            ds_msg.add_field(f, v)
        net_msg.add_dataset_message(ds_msg)
        _ = net_msg.encode_minimal()
        
        t1 = time.ticks_us()
        uadp_min_times.append(time.ticks_diff(t1, t0))
    
    def calc_stats(times):
        avg = sum(times) / len(times)
        min_t = min(times)
        max_t = max(times)
        return {"mean_us": avg, "min_us": min_t, "max_us": max_t}
    
    json_stats = calc_stats(json_times)
    uadp_stats = calc_stats(uadp_times)
    uadp_min_stats = calc_stats(uadp_min_times)
    
    speedup = json_stats["mean_us"] / uadp_stats["mean_us"]
    speedup_min = json_stats["mean_us"] / uadp_min_stats["mean_us"]
    
    return {
        "iterations": num_iterations,
        "fields": num_fields,
        "json": json_stats,
        "uadp": uadp_stats,
        "uadp_minimal": uadp_min_stats,
        "speedup": round(speedup, 2),
        "speedup_minimal": round(speedup_min, 2)
    }


# =============================================================================
# Exemplo de Uso
# =============================================================================

def example_usage():
    """Demonstra uso bÃ¡sico do UADP."""
    print("\n" + "="*50)
    print("OPC UA PubSub UADP - Exemplo")
    print("="*50)
    
    # 1. Comparar tamanhos
    print("\n[1] ComparaÃ§Ã£o de tamanho JSON vs UADP:")
    data = {
        "Temperature": 25.5,
        "Humidity": 60,
        "Pressure": 1013.25,
        "Status": True,
        "Counter": 12345
    }
    
    comparison = compare_encoding_size(data)
    print(f"    JSON:         {comparison['json_bytes']} bytes")
    print(f"    UADP:         {comparison['uadp_bytes']} bytes ({comparison['savings_percent']}% menor)")
    print(f"    UADP Minimal: {comparison['uadp_minimal_bytes']} bytes ({comparison['savings_minimal_percent']}% menor)")
    print(f"    Ratio:        {comparison['ratio']}x")
    
    # 2. Benchmark de serializaÃ§Ã£o
    print("\n[2] Benchmark de serializaÃ§Ã£o (100 iteraÃ§Ãµes, 5 campos):")
    bench = benchmark_encoding(100, 5)
    print(f"    JSON:         {bench['json']['mean_us']:.1f} Âµs")
    print(f"    UADP:         {bench['uadp']['mean_us']:.1f} Âµs ({bench['speedup']}x mais rÃ¡pido)")
    print(f"    UADP Minimal: {bench['uadp_minimal']['mean_us']:.1f} Âµs ({bench['speedup_minimal']}x mais rÃ¡pido)")
    
    # 3. Criar mensagem UADP
    print("\n[3] Criando mensagem UADP:")
    net_msg = UADPNetworkMessage("ESP32-UADP-001", writer_group_id=100)
    
    ds_msg = UADPDataSetMessage(dataset_writer_id=1000, sequence_number=1)
    ds_msg.add_field("Temperature", 25.5, OPCUATypes.FLOAT)
    ds_msg.add_field("Humidity", 60, OPCUATypes.INT32)
    ds_msg.add_field("Status", True, OPCUATypes.BOOLEAN)
    
    net_msg.add_dataset_message(ds_msg)
    
    payload = net_msg.encode()
    print(f"    Payload: {len(payload)} bytes")
    print(f"    Hex: {payload.hex()}")
    
    # 4. Decodificar mensagem
    print("\n[4] Decodificando mensagem:")
    decoded = UADPNetworkMessage.decode(payload)
    if decoded:
        print(f"    PublisherId: {decoded.publisher_id}")
        print(f"    WriterGroupId: {decoded.writer_group_id}")
        print(f"    DataSetMessages: {decoded._ds_count}")
    
    print("\n[OK] MÃ³dulo UADP funcionando!")
    return True


# Executa exemplo ao importar (pode comentar em produÃ§Ã£o)
if __name__ == "__main__":
    example_usage()