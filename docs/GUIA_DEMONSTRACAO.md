# Guia de demonstração da célula

Onde encontrar e como mostrar cada parte da célula funcionando, do braço ao gêmeo digital.
Arquitetura, DataSet e histórico de testes: [CELULA_ROBOTICA.md](CELULA_ROBOTICA.md).
Instalação do RPi: [deploy/rpi5/README.md](../deploy/rpi5/README.md).

Tudo abaixo é feito **do PC, pelo cabo** (`169.254.14.189`). Nada aqui comanda o braço: a TI só lê.

## 1. Conferir que está tudo no ar (30 s)

```
python deploy/pc/verificar_celula.py
```

O script confere, em uma tela: SSH e hora do RPi, os 6 serviços, os 4 contêineres do BaSyx, as
6 páginas/APIs, as mensagens MQTT chegando, o IP da ESP32 IT no broker e o último valor do AAS.
Termina com `Tudo no ar.` (código de saída 0) ou com o número de itens com problema.

Resultado em 2026-11-24 (célula montada, RPi ligado havia 1 h 10 min):

```
  [OK ] SSH                          AAS | up 1 hour, 10 minutes | 2026-11-24 19:45:27 -04
  [OK ] Hora (chrony)                fonte 169.254.124.59
  [OK ] mosquitto / nodered / aas-gateway / chrony / xrdp / docker    active
  [OK ] aas-env                      eclipsebasyx/aas-environment:2.0.0-milestone-16  (healthy)
  [OK ] aas-registry                 eclipsebasyx/aas-registry-log-mem:2.0.0-milestone-16  (healthy)
  [OK ] sm-registry                  eclipsebasyx/submodel-registry-log-mem:2.0.0-milestone-16  (healthy)
  [OK ] aas-web-ui                   eclipsebasyx/aas-gui:v2-261013
  [OK ] Dashboard Node-RED, Editor Node-RED, AAS Web UI, 8081, 8082, 8083     (HTTP 200)
  [OK ] MQTT (OPC UA PubSub)         14 mensagens em 5 s; Seq=11015 hora=2026-11-24T23:45:32Z
  [OK ] ESP32 IT no broker           192.168.0.100
  [OK ] AAS OperationalData          LastUpdate=2026-11-24T23:45:33Z Ciclo=2 Fase=1 Peça=true
Tudo no ar.
```

Nesse dia também foi conferido que o que roda no RPi é igual ao repositório: flow do Node-RED,
`mosquitto`, `chrony`, `aas-gateway.service`, os 3 arquivos do BaSyx e o `aas_gateway.py`.

## 2. Roteiro para mostrar (ordem sugerida)

Segue o caminho do dado, da OT para a TI. Para os valores mudarem na tela, rode um ciclo
automático: peça na frente do sensor e botão A da IHM (~22 s por ciclo, `CycleCount` sobe 1).

| # | O que mostrar | Onde | O que apontar |
|---|---|---|---|
| 1 | Braço, esteira, HC-SR04, LCD e botões | bancada (placa OT, ESP-IDF) | a OT não tem rede: só o cabo serial J7 (Modbus RTU, escravo 1, 115200 8N1) |
| 2 | Gateway de borda | bancada (placa IT, MicroPython): LCD + Nokia 5110 | lê os 9 registradores por Modbus e publica OPC UA PubSub JSON por Wi-Fi (`OPC_UA`) |
| 3 | Mensagens PubSub cruas | terminal: `ssh rpi5 "mosquitto_sub -t it/opcua/celula_robotica -v"` | NetworkMessage `ua-data`, `SequenceNumber` subindo, `SourceTimestamp` em UTC, ~2,8 msg/s |
| 4 | Assinante OPC UA genérico | Prosys OPC UA Browser no PC → PubSub, broker `mqtt://169.254.14.189:1883` | um cliente OPC UA de mercado lê o DataSet sem adaptação (campos em [CELULA_ROBOTICA.md](CELULA_ROBOTICA.md#prosys-opc-ua-browser-assinante-pubsub)) |
| 5 | Dashboard (push) | http://169.254.14.189:1880/dashboard/celula | juntas, esteira, sensor, peça, ciclo e fase ao vivo |
| 6 | Flow do Node-RED | http://169.254.14.189:1880 | aba "Célula robótica": nó MQTT in → funções → widgets |
| 7 | Gêmeo digital (pull) | AAS Web UI: http://169.254.14.189:3000 | AAS `CelulaRoboticaAAS` com `Nameplate`, `OperationalData`, `OPCUAPubSubInfo`; ligar o "Auto Sync" para ver os valores mudando |
| 8 | API AAS Part 2 | navegador: http://169.254.14.189:8081/shells e `/submodels` | o mesmo AAS em JSON padronizado; valores: `/submodels/<id>/$value` (abaixo) |
| 9 | Arquivo AASX | `~/aas/celula_robotica.aasx` no RPi (`scp rpi5:aas/celula_robotica.aasx .`) → AASX Package Explorer | foto do AAS, regravada a cada 60 s |
| 10 | Bastidores | `ssh rpi5` ou `mstsc` → `169.254.14.189` (sair pelo Logout) | serviços, contêineres e logs (seção 4) |

Valores do `OperationalData` direto da API:

```
http://169.254.14.189:8081/submodels/dXJuOnVlYTpjZWx1bGEtcm9ib3RpY2E6c3VibW9kZWw6b3BlcmF0aW9uYWwtZGF0YQ/$value
```

```json
{"JointBase": "90.0", "JointShoulder": "90.0", "JointElbow": "180.0", "JointGripper": "90.0",
 "ConveyorSpeed": "0", "ConveyorRunning": "false", "SensorDistance": "7", "PieceDetected": "true",
 "CycleCount": "2", "AutoPhase": "1", "LastUpdate": "2026-11-24T23:44:25Z"}
```

## 3. Endereços e portas

| Serviço | Porta | Endereço (pelo cabo) | Quem usa |
|---|---|---|---|
| Mosquitto (MQTT) | 1883 | `mqtt://169.254.14.189:1883`; a IT usa `192.168.0.2:1883` (Wi-Fi) | IT publica; aas-gateway, Node-RED e Prosys assinam |
| Node-RED + Dashboard 2.0 | 1880 | http://169.254.14.189:1880 , `/dashboard/celula` | navegador |
| BaSyx AAS Environment (repositório de AAS, submodelos e concept descriptions) | 8081 | http://169.254.14.189:8081 | aas-gateway escreve; Web UI e clientes leem |
| BaSyx AAS Registry | 8082 | http://169.254.14.189:8082/shell-descriptors | Web UI |
| BaSyx Submodel Registry | 8083 | http://169.254.14.189:8083/submodel-descriptors | Web UI |
| BaSyx AAS Web UI | 3000 | http://169.254.14.189:3000 | navegador |
| chrony (NTP) | 123/udp | RPi serve a hora para a IT; pega do PC `169.254.124.59` | IT |
| xrdp | 3389 | `mstsc` → `169.254.14.189` | desktop do RPi |
| SSH | 22 | `ssh rpi5` | terminal |

Sem senha em nenhum serviço (fase de testes; ver Pendências em [CELULA_ROBOTICA.md](CELULA_ROBOTICA.md#pendências)).

## 4. Onde está cada coisa no RPi

| O quê | No RPi | No repositório | Ver / reiniciar |
|---|---|---|---|
| Mosquitto | `/etc/mosquitto/conf.d/celula.conf` | [deploy/rpi5/mosquitto-celula.conf](../deploy/rpi5/mosquitto-celula.conf) | `systemctl status mosquitto` |
| Node-RED | `~/.node-red/flows.json`, `package.json` | [deploy/rpi5/nodered-celula.json](../deploy/rpi5/nodered-celula.json) | `journalctl -u nodered -f` |
| Gateway AAS | `~/aas/aas_gateway.py` (venv em `~/aas/venv`, BaSyx Python SDK + paho), gera `~/aas/celula_robotica.aasx` e `celula_robotica_aas.json` | [examples/aas_digital_twin/aas_gateway.py](../examples/aas_digital_twin/aas_gateway.py), [deploy/rpi5/aas-gateway.service](../deploy/rpi5/aas-gateway.service) | `journalctl -u aas-gateway -f` (uma linha por mensagem: Seq, juntas, peça, ciclo, fase, `→ BaSyx`) |
| Eclipse BaSyx | `~/basyx/docker-compose.yml`, `aas-env.properties`, `registry.yml` | [deploy/rpi5/basyx/](../deploy/rpi5/basyx/) | seção 5 |
| chrony | `/etc/chrony/conf.d/celula.conf` | [deploy/rpi5/chrony-celula.conf](../deploy/rpi5/chrony-celula.conf) | `chronyc sources` (`^*` = PC) |
| Chromium no xrdp | `/etc/chromium.d/zz-xrdp-sem-gpu` | [deploy/rpi5/chromium-xrdp-sem-gpu](../deploy/rpi5/chromium-xrdp-sem-gpu) | — |
| Rede | NetworkManager: `OPC_UA` (wlan0 `192.168.0.2`), `netplan-eth0` (`169.254.14.189`) | [deploy/rpi5/README.md](../deploy/rpi5/README.md) | `ip -br a`, `nmcli con show --active` |

Sistema: Raspberry Pi 5 8 GB, Debian 13 (trixie) 64-bit, kernel 6.18; Docker 26.1.5, Compose
2.26.1, Node-RED 5.0.9 (`@flowfuse/node-red-dashboard` 1.36). SD de 15 GB com 3,8 GB livres;
memória usada ~1,7 GB de 7,9 GB; temperatura ~52 °C.

## 5. Pacotes Docker (Eclipse BaSyx)

Um projeto Compose, `basyx`, em `~/basyx`. Todos com `restart: unless-stopped` (sobem sozinhos no
boot) e **sem volumes**: o BaSyx guarda tudo em memória e o `aas-gateway` reenvia o AAS inteiro
quando ele reinicia.

| Contêiner | Imagem | Tamanho | Porta (host→contêiner) | Memória (RSS) |
|---|---|---|---|---|
| `aas-env` | `eclipsebasyx/aas-environment:2.0.0-milestone-16` | 621 MB | 8081→8081 | ~575 MB |
| `aas-registry` | `eclipsebasyx/aas-registry-log-mem:2.0.0-milestone-16` | 521 MB | 8082→8080 | ~330 MB |
| `sm-registry` | `eclipsebasyx/submodel-registry-log-mem:2.0.0-milestone-16` | 521 MB | 8083→8080 | ~330 MB |
| `aas-web-ui` | `eclipsebasyx/aas-gui:v2-261013` | 233 MB | 3000→3000 | — |

Comandos (no RPi, `ssh rpi5`):

```
sudo docker compose -f ~/basyx/docker-compose.yml ls     # projeto "basyx running(4)"
sudo docker ps                                           # contêineres, estado (healthy) e portas
sudo docker images                                       # as 4 imagens
sudo docker logs --tail 50 aas-env                       # log de um contêiner
cd ~/basyx && sudo docker compose restart                # reiniciar o BaSyx (o AAS volta em ~1 min)
curl -s localhost:8081/actuator/health                   # {"status":"UP",...}
```

O `docker stats` mostra `0B` de memória porque o kernel do RPi não liga o cgroup de memória; para
ver o consumo: `ps -eo rss,args --sort=-rss | grep java`.

O tempo "Up 2 weeks" do `docker ps` não é real: o RPi não tem bateria no RTC e liga sempre com a
hora de 09/11; o `chrony` adianta o relógio depois que os contêineres já subiram. O tempo certo
desde o boot é o do `uptime`.

## 6. Mostrar ao vivo pelo terminal

Um bloco para colar no PowerShell durante a apresentação:

```
ssh rpi5 "systemctl is-active mosquitto nodered aas-gateway chrony docker; sudo docker ps --format 'table {{.Names}}\t{{.Image}}\t{{.Status}}\t{{.Ports}}'"
ssh rpi5 "mosquitto_sub -t it/opcua/celula_robotica -C 1"           # uma mensagem OPC UA PubSub
ssh rpi5 "journalctl -u aas-gateway -n 5 --no-pager"                 # MQTT → AAS → BaSyx
ssh rpi5 "ss -tn state established '( sport = :1883 )'"              # quem está ligado ao broker (IT = 192.168.0.100)
ssh rpi5 "chronyc sources"                                           # hora vinda do PC
```

## 7. Se algo não estiver no ar

| Sintoma | Verificar |
|---|---|
| `ssh rpi5` não responde | cabo de rede, IP fixo do PC (`deploy/pc/fixar-ip-cabo.ps1`) |
| MQTT sem mensagens / IT fora do broker | Wi-Fi `OPC_UA` ligado; placa IT ligada (Nokia 5110 mostra o estado); a IT tenta o Wi-Fi a cada ~15 s e o broker a cada 3 s |
| IT no broker, mas sem dados novos | cabo J7 entre IT e OT; placa OT ligada |
| Web UI vazia | `sudo docker ps` (4 contêineres); `journalctl -u aas-gateway` deve mostrar `→ BaSyx` |
| Web UI com valores parados | ligar o "Auto Sync" ou recarregar a página (é pull) |
| Hora errada nas mensagens | `chronyc sources` precisa de `^*`; a IT refaz o NTP a cada 60 s |
