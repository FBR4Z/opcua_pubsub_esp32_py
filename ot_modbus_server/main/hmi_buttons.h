#pragma once

// Configura os 3 botões (GPIO34/35/36) e inicia a task que faz o jog
// manual (ciclar eixo, incrementar/decrementar) espelhando o LCD.
// Chamar depois de servo_driver_init(), conveyor_driver_init() e
// lcd_driver_init().
void hmi_buttons_start(void);