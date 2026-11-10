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
| `nodered` (+ `@flowfuse/node-red-dashboard`) | 1880 | [nodered-celula.json](nodered-celula.json) (flow); dashboard em `http://<RPi>:1880/dashboard/celula` |
| `aas-gateway` | — | [aas-gateway.service](aas-gateway.service) → `/etc/systemd/system/`; script em `~/aas/` |
| BaSyx (Docker): `aas-env`, `aas-registry`, `sm-registry`, `aas-web-ui` | 8081, 8082, 8083, 3000 | [basyx/](basyx/) → `~/basyx/`; Web UI em `http://169.254.14.189:3000` |
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

# servidor AAS (Eclipse BaSyx, ~1,9 GB de imagens; precisa de internet)
sudo apt-get install -y docker.io docker-compose && sudo usermod -aG docker engfb
mkdir -p ~/basyx && cp basyx/* ~/basyx/ && cd ~/basyx && sudo docker compose up -d

# flow da célula (substitui todos os flows do Node-RED)
curl -X POST http://localhost:1880/flows -H "Content-Type: application/json"      -H "Node-RED-Deployment-Type: full" --data @nodered-celula.json
```

## Hora (NTP)

O RPi fica sem internet no `wlan0`, então a referência de hora é o PC pelo cabo:
PC (w32time, sincronizado com `a.ntp.br`) → RPi (`chrony`, serve `192.168.0.0/24`) → ESP32
(`ntptime.host = "192.168.0.2"`, pendente).

- No PC, uma vez, como Administrador: [../pc/habilitar-servidor-ntp.ps1](../pc/habilitar-servidor-ntp.ps1)
  (liga o servidor NTP do Windows e abre UDP 123 e ping só para `169.254.0.0/16`).
- Conferir: `chronyc sources` deve mostrar `^* 169.254.124.59`.

## AAS

O `aas-gateway` cria o AAS no BaSyx ao iniciar (PUT, ou POST se ainda não existir) e atualiza
`OperationalData` e `OPCUAPubSubInfo` 1x por segundo pela API AAS Part 2. O BaSyx guarda tudo em
memória: se ele reiniciar, o gateway reenvia o AAS inteiro sozinho. O `.aasx` em `~/aas/` é
regravado só a cada 60 s (cartão SD).

- Web UI: `http://169.254.14.189:3000`; API: `http://169.254.14.189:8081/shells`.
- Valores ao vivo: `GET /submodels/<id em base64url>/$value`.

## Pendente

- Hora no boot: sem bateria no RTC, o RPi liga com a hora do último desligamento e o `chrony` só
  corrige ~20 s depois (teste de 2026-11-09: salto de 3035 s). `aas-gateway` e `nodered` sobem antes,
  então as primeiras mensagens podem sair com hora errada. Opções: `After=time-sync.target` +
  `chrony-wait.service` nos serviços, ou bateria ML-2020 no conector J5 do RPi 5.
- Gateway IT: com MQTT QoS 0 sem keepalive, uma conexão TCP "meio morta" (ex.: RPi trocou de
  rede) só é percebida quando o TCP do ESP32 desiste (~5 min em 2026-11-09). Usar ping MQTT
  com timeout para reconectar em segundos.
- Reserva DHCP de `192.168.0.2` para o MAC `88:a2:9e:10:6a:c2` na página do roteador.
- `config.py` dos ESP32: Wi-Fi `OPC_UA`, `MQTT_BROKER = "192.168.0.2"` e `ntptime`.
- Senha no Mosquitto antes de sair da fase de testes.
