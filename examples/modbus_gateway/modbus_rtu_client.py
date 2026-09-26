"""
Modbus RTU Client (antigo "Master") minimalista para MicroPython.

Implementa apenas o necessário para este projeto:
- Function code 0x03 (Read Holding Registers)
- CRC16 padrão Modbus
- Timeout simples via UART (sem o silêncio de 3.5 caracteres formal do
  padrão — para ponto-a-ponto com 2 dispositivos isso é uma simplificação
  aceitável; documentar essa escolha na dissertação se for o caso).
"""

from machine import UART
import time


def _crc16_modbus(data: bytes) -> int:
    crc = 0xFFFF
    for byte in data:
        crc ^= byte
        for _ in range(8):
            if crc & 0x0001:
                crc = (crc >> 1) ^ 0xA001
            else:
                crc >>= 1
    return crc


class ModbusRTUClient:
    def __init__(self, uart_id=2, tx=17, rx=16, baudrate=115200, timeout_ms=200):
        self.uart = UART(uart_id, baudrate=baudrate, tx=tx, rx=rx,
                          bits=8, parity=None, stop=1, timeout=timeout_ms)
        self.timeout_ms = timeout_ms

    def read_holding_registers(self, slave_addr: int, start_reg: int, qty: int):
        """Function code 0x03. Retorna lista de uint16 ou None em caso de erro/timeout."""
        request = bytes([
            slave_addr,
            0x03,
            (start_reg >> 8) & 0xFF, start_reg & 0xFF,
            (qty >> 8) & 0xFF, qty & 0xFF,
        ])
        crc = _crc16_modbus(request)
        request += bytes([crc & 0xFF, (crc >> 8) & 0xFF])

        # limpa qualquer lixo pendente antes de enviar
        if self.uart.any():
            self.uart.read()

        self.uart.write(request)

        expected_len = 3 + 2 * qty + 2  # addr + func + byte_count + dados + crc
        response = self._read_exact(expected_len)
        if response is None:
            return None

        if response[0] != slave_addr or response[1] != 0x03:
            return None  # resposta inesperada ou exceção Modbus (func | 0x80)

        recv_crc = response[-2] | (response[-1] << 8)
        calc_crc = _crc16_modbus(response[:-2])
        if recv_crc != calc_crc:
            return None  # CRC inválido — frame corrompido

        byte_count = response[2]
        values = []
        for i in range(0, byte_count, 2):
            hi = response[3 + i]
            lo = response[3 + i + 1]
            values.append((hi << 8) | lo)
        return values

    def _read_exact(self, n_bytes: int):
        """Lê até n_bytes, respeitando o timeout configurado no UART."""
        buf = b""
        deadline = time.ticks_add(time.ticks_ms(), self.timeout_ms)
        while len(buf) < n_bytes:
            if time.ticks_diff(deadline, time.ticks_ms()) <= 0:
                return None
            chunk = self.uart.read(n_bytes - len(buf))
            if chunk:
                buf += chunk
        return buf