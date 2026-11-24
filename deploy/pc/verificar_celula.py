"""Confere, do PC (pelo cabo), se a célula está toda no ar.

Uso:  python deploy/pc/verificar_celula.py
Só biblioteca padrão; precisa do `ssh rpi5` configurado (ver deploy/rpi5/README.md).
Não manda nada para os ESP32: só lê o RPi e as páginas/APIs.
"""

import base64
import json
import subprocess
import sys
import urllib.request

RPI = "169.254.14.189"
SERVICOS = ["mosquitto", "nodered", "aas-gateway", "chrony", "xrdp", "docker"]
CONTAINERS = ["aas-env", "aas-registry", "sm-registry", "aas-web-ui"]
PAGINAS = [
    ("Dashboard Node-RED", f"http://{RPI}:1880/dashboard/celula"),
    ("Página Sistema", f"http://{RPI}:1880/dashboard/sistema"),
    ("Editor Node-RED", f"http://{RPI}:1880/"),
    ("AAS Web UI (BaSyx)", f"http://{RPI}:3000/"),
    ("AAS Environment", f"http://{RPI}:8081/shells"),
    ("Registro de AAS", f"http://{RPI}:8082/shell-descriptors"),
    ("Registro de submodelos", f"http://{RPI}:8083/submodel-descriptors"),
]
SM_OPER = "urn:uea:celula-robotica:submodel:operational-data"
TOPICO = "it/opcua/celula_robotica"

falhas = 0


def linha(ok, nome, detalhe=""):
    global falhas
    falhas += not ok
    print(f"  [{'OK ' if ok else 'ERRO'}] {nome:28s} {detalhe}")


def ssh(cmd, timeout=20):
    r = subprocess.run(["ssh", "-o", "ConnectTimeout=8", "rpi5", cmd],
                       capture_output=True, text=True, encoding="utf-8",
                       errors="replace", timeout=timeout)
    return r.stdout.strip()


def http(url):
    try:
        with urllib.request.urlopen(url, timeout=5) as r:
            return r.status, r.read()
    except Exception as e:
        return None, str(e).encode()


print(f"RPi 5 'AAS' ({RPI})")
try:
    info = ssh("hostname; uptime -p; date '+%F %T %Z'; "
               "chronyc -n sources | grep '^\\^\\*' | awk '{print $2}'")
except Exception as e:
    info = ""
    print("  ssh falhou:", e)
info = info.splitlines()
linha(len(info) >= 3, "SSH", " | ".join(info[:3]))
linha(len(info) >= 4, "Hora (chrony)", f"fonte {info[3]}" if len(info) >= 4 else "sem fonte NTP")

print("\nServiços (systemd)")
ativos = ssh("systemctl is-active " + " ".join(SERVICOS)).splitlines()
for nome, est in zip(SERVICOS, ativos + [""] * len(SERVICOS)):
    linha(est == "active", nome, est)

print("\nContêineres do Eclipse BaSyx (Docker)")
ps = ssh("sudo docker ps --format '{{.Names}}|{{.Image}}|{{.Status}}'")
estado = {l.split("|")[0]: l.split("|")[1:] for l in ps.splitlines() if "|" in l}
for c in CONTAINERS:
    img, st = estado.get(c, ["-", "parado"])
    ok = st.startswith("Up") and "unhealthy" not in st
    # o tempo de "Up" não vale: o RPi liga com a hora de 09/11 (sem RTC) e o chrony a adianta
    linha(ok, c, f"{img}  ({'healthy' if 'healthy' in st else 'rodando' if ok else st})")

print("\nPáginas e APIs (do PC, pelo cabo)")
for nome, url in PAGINAS:
    st, _ = http(url)
    linha(st == 200, nome, url)

print("\nDados ao vivo")
amostra = ssh(f"timeout 6 mosquitto_sub -h localhost -t {TOPICO} -C 40 -W 5 2>/dev/null")
msgs = [json.loads(l) for l in amostra.splitlines() if l.startswith("{")]
if msgs:
    m = msgs[-1]["Messages"][0]
    p = m["Payload"]
    linha(True, "MQTT (OPC UA PubSub)",
          f"{len(msgs)} mensagens em 5 s; Seq={m['SequenceNumber']} "
          f"hora={p['JointBase']['SourceTimestamp']}")
else:
    linha(False, "MQTT (OPC UA PubSub)", f"nada em '{TOPICO}' em 5 s (IT ligada?)")
ip_it = ssh("ss -Htn state established '( sport = :1883 )' | awk '{print $4}' "
            "| grep -v 127.0.0.1 | cut -d: -f1 | sort -u")
linha(bool(ip_it), "ESP32 IT no broker", ip_it.replace("\n", ", ") or "não conectada")

sid = base64.urlsafe_b64encode(SM_OPER.encode()).decode().rstrip("=")
st, corpo = http(f"http://{RPI}:8081/submodels/{sid}/$value")
if st == 200:
    v = json.loads(corpo)
    linha(True, "AAS OperationalData",
          f"LastUpdate={v.get('LastUpdate')} Ciclo={v.get('CycleCount')} "
          f"Fase={v.get('AutoPhase')} Peça={v.get('PieceDetected')}")
else:
    linha(False, "AAS OperationalData", corpo.decode()[:80])

print("\n" + ("Tudo no ar." if not falhas else f"{falhas} item(ns) com problema."))
sys.exit(1 if falhas else 0)
