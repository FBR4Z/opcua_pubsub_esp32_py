#pragma once

// Registra os comandos (eixo, ir, ler, soltar) e inicia o console REPL
// na UART0 (a mesma do monitor serial). Chamar uma vez no boot, depois
// de servo_driver_init().
void console_cmds_start(void);
