# RPi 5 da célula (Mosquitto + Node-RED + AAS)

Raspberry Pi 5 8 GB, hostname `AAS`, Raspberry Pi OS (Debian 13 trixie, 64-bit), configurado
só por SSH (sem tela).

```
ESP32 OT --Modbus RTU--> ESP32 IT --Wi-Fi--> roteador da célula --Wi-Fi (wlan0)--> RPi 5 --cabo (eth0)--> PC
```

| Interface | Rede | Endereço |
|---|---|---|
| `wlan0` | roteador da célula, SSID `OPC_UA` (sem internet) | **`192.168.0.2/24`** fixo, gateway/DNS `192.168.0.1` — broker MQTT dos ESP32 |
| `eth0` | cabo direto ao PC | **`169.254.14.189/16`** fixo, sem rota padrão |
| PC, placa `Ethernet` | cabo direto ao RPi | **`169.254.124.59/16`** fixo ([../pc/fixar-ip-cabo.ps1](../pc/fixar-ip-cabo.ps1)) |

- MAC do `wlan0`: `88:a2:9e:10:6a:c2` (reservar `192.168.0.2` no DHCP do roteador).
- A rede de casa (`netplan-wlan0-FABIO`) ficou salva com `autoconnect no`; para baixar pacotes:
  `sudo nmcli con up netplan-wlan0-FABIO` e depois `sudo nmcli con up OPC_UA`.
- No PC, `ssh rpi5` aponta para `169.254.14.189` (o `AAS.local` pode resolver pelo Wi-Fi e cair
  quando o `wlan0` troca de rede).

## Serviços

| Serviço | Porta | Arquivo |
|---|---|---|
| `mosquitto` | 1883 | [mosquitto-celula.conf](mosquitto-celula.conf) → `/etc/mosquitto/conf.d/celula.conf` |
| `nodered` (+ `@flowfuse/node-red-dashboard`) | 1880 | `~/.node-red/` |
| `aas-gateway` | — | [aas-gateway.service](aas-gateway.service) → `/etc/systemd/system/`; script em `~/aas/` |
| `chrony` | 123/udp | [chrony-celula.conf](chrony-celula.conf) → `/etc/chrony/conf.d/celula.conf` |
| `xrdp` | 3389 | desktop pelo `mstsc` (sessão Xorg); o desktop local não sobe no boot |

## Instalação (refazer do zero)

1. Raspberry Pi Imager: hostname `AAS`, usuário `engfb`, Wi-Fi com internet, SSH só por chave.
2. No RPi: `echo "engfb ALL=(ALL) NOPASSWD:ALL" | sudo tee /etc/sudoers.d/010-engfb-nopasswd`.
3. Do PC (copie com `scp`: o pipe do PowerShell grava BOM e quebra os acentos):

```
sudo apt-get update && sudo apt-get full-upgrade -y
sudo apt-get install -y mosquitto mosquitto-clients xrdp python3-venv chrony
sudo install -m 644 mosquitto-celula.conf /etc/mosquitto/conf.d/celula.conf
sudo systemctl restart mosquitto
sudo install -m 644 chrony-celula.conf /etc/chrony/conf.d/celula.conf
sudo systemctl restart chrony

mkdir -p ~/aas && cp aas_gateway.py requirements.txt ~/aas/    # de examples/aas_digital_twin
cd ~/aas && python3 -m venv venv && venv/bin/pip install -r requirements.txt
sudo install -m 644 aas-gateway.service /etc/systemd/system/
sudo systemctl daemon-reload && sudo systemctl enable --now aas-gateway

curl -fsSL https://raw.githubusercontent.com/node-red/linux-installers/master/deb/update-nodejs-and-nodered -o nr.sh
bash nr.sh --confirm-install --confirm-pi --nodered-user=engfb
# o instalador para no assistente `node-red admin init`: encerre esse processo
sudo systemctl enable --now nodered
cd ~/.node-red && npm install @flowfuse/node-red-dashboard && sudo systemctl restart nodered

sudo nmcli con modify netplan-eth0 ipv4.method auto ipv4.link-local fallback \
     ipv4.may-fail yes ipv4.never-default yes ipv6.method link-local
sudo systemctl set-default multi-user.target
```

## Hora (NTP)

O RPi fica sem internet no `wlan0`, então a referência de hora é o PC pelo cabo:
PC (w32time, sincronizado com `a.ntp.br`) → RPi (`chrony`, serve `192.168.0.0/24`) → ESP32
(`ntptime.host = "192.168.0.2"`, pendente).

- No PC, uma vez, como Administrador: [../pc/habilitar-servidor-ntp.ps1](../pc/habilitar-servidor-ntp.ps1)
  (liga o servidor NTP do Windows e abre UDP 123 e ping só para `169.254.0.0/16`).
- Conferir: `chronyc sources` deve mostrar `^* 169.254.124.59`.

## Pendente

- Reserva DHCP de `192.168.0.2` para o MAC `88:a2:9e:10:6a:c2` na página do roteador.
- `config.py` dos ESP32: Wi-Fi `OPC_UA`, `MQTT_BROKER = "192.168.0.2"` e `ntptime`.
- Flow do Node-RED da célula (assinando `it/opcua/celula_robotica`).
- Senha no Mosquitto antes de sair da fase de testes.
