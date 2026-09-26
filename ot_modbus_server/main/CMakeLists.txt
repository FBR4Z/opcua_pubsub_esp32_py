idf_component_register(SRCS "main.c" "servo_driver.c" "console_cmds.c" "conveyor_driver.c" "hc_sr04_driver.c" "lcd_driver.c" "hmi_buttons.c"
                        INCLUDE_DIRS "."
                        REQUIRES driver esp_driver_ledc esp_driver_uart esp_driver_gpio esp_driver_i2c esp_timer console)