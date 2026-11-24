#!/usr/bin/env python3
"""Estado do RPi da célula em JSON, para a página /dashboard/sistema do Node-RED.

Instalar: cp celula_status.py ~/aas/   (o Node-RED chama a cada 5 s pelo nó exec)
Testar:   python3 ~/aas/celula_status.py
Só lê: systemctl, docker (usuário no grupo docker), ss, /proc e a API do BaSyx.

O tempo "no ar" vem de /proc/<pid>/stat (relativo ao boot), não do relógio: o RPi liga com a
hora de 09/11 (sem bateria no RTC), e o "Up 2 weeks" do docker ps sai errado.
"""

import base64
import json
import os
import shutil
import socket
import subprocess
import time
import urllib.request

SERVICOS = [
    ("mosquitto", "Broker MQTT (transporte do OPC UA PubSub)"),
    ("nodered", "Node-RED + Dashboard"),
    ("aas-gateway", "MQTT → AAS (BaSyx Python SDK) → BaSyx"),
    ("docker", "Motor dos contêineres do BaSyx"),
    ("chrony", "NTP: hora do PC para os ESP32"),
    ("xrdp", "Área de trabalho remota (mstsc)"),
]
FUNCAO = {
    "aas-env": "AAS Environment: repositório de AAS e submodelos (API Part 2)",
    "aas-registry": "Registro de AAS (shell descriptors)",
    "sm-registry": "Registro de submodelos",
    "aas-web-ui": "AAS Web UI (navegador)",
}
BASYX = "http://localhost:8081"
SM_OPER = "urn:uea:celula-robotica:submodel:operational-data"
HZ = os.sysconf("SC_CLK_TCK")


def sh(*cmd):
    try:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=10).stdout
    except Exception:
        return ""


def uptime_s():
    with open("/proc/uptime") as f:
        return float(f.read().split()[0])


def no_ar(pid):
    """Segundos desde que o processo começou (0 se não existe)."""
    try:
        with open(f"/proc/{pid}/stat") as f:
            inicio = int(f.read().rsplit(")", 1)[1].split()[19]) / HZ
        return round(uptime_s() - inicio)
    except Exception:
        return 0


def rss_mb(pid):
    """Memória (VmRSS) do processo e dos filhos diretos, em MB."""
    total = 0
    pids = [str(pid)] + sh("pgrep", "-P", str(pid)).split()
    for p in pids:
        try:
            with open(f"/proc/{p}/status") as f:
                for l in f:
                    if l.startswith("VmRSS:"):
                        total += int(l.split()[1])
        except Exception:
            pass
    return round(total / 1024)


def servicos():
    out = []
    for nome, desc in SERVICOS:
        props = dict(l.split("=", 1) for l in sh(
            "systemctl", "show", nome, "-p", "ActiveState,SubState,MainPID,UnitFileState"
        ).splitlines() if "=" in l)
        pid = int(props.get("MainPID", "0") or 0)
        out.append({"nome": nome, "funcao": desc, "estado": props.get("ActiveState", "?"),
                    "sub": props.get("SubState", ""), "boot": props.get("UnitFileState", ""),
                    "pid": pid, "no_ar_s": no_ar(pid) if pid else 0,
                    "mem_mb": rss_mb(pid) if pid else 0})
    return out


def conteineres():
    out = []
    for l in sh("docker", "ps", "-a", "--format", "{{json .}}").splitlines():
        try:
            c = json.loads(l)
        except ValueError:
            continue
        nome = c["Names"]
        insp = sh("docker", "inspect", "-f",
                  "{{.State.Pid}}|{{if .State.Health}}{{.State.Health.Status}}{{end}}|"
                  "{{.HostConfig.RestartPolicy.Name}}|"
                  "{{index .Config.Labels \"com.docker.compose.project\"}}", nome).strip()
        pid, saude, restart, projeto = (insp.split("|") + ["", "", "", ""])[:4]
        pid = int(pid or 0)
        portas = sorted({p.split("->")[0].split(":")[-1] + "→" + p.split("->")[1].split("/")[0]
                         for p in c.get("Ports", "").split(", ") if "->" in p})
        out.append({"nome": nome, "funcao": FUNCAO.get(nome, ""), "imagem": c["Image"],
                    "estado": c["State"], "saude": saude, "portas": portas,
                    "restart": restart, "projeto": projeto,
                    "no_ar_s": no_ar(pid) if pid else 0, "mem_mb": rss_mb(pid) if pid else 0})
    ordem = list(FUNCAO)
    return sorted(out, key=lambda c: ordem.index(c["nome"]) if c["nome"] in ordem else 99)


def broker():
    clientes = []
    for l in sh("ss", "-Htn", "state", "established", "( sport = :1883 )").splitlines():
        partes = l.split()
        if len(partes) >= 4:
            ip = partes[3].rsplit(":", 1)[0]
            clientes.append("RPi (local)" if ip.startswith("127.") else ip)
    locais = clientes.count("RPi (local)")
    externos = sorted(set(c for c in clientes if c != "RPi (local)"))
    return {"clientes_locais": locais, "clientes_rede": externos}


def aas():
    r = {"ok": False}
    try:
        with urllib.request.urlopen(BASYX + "/shells", timeout=3) as f:
            r["shells"] = [s["idShort"] for s in json.load(f)["result"]]
        with urllib.request.urlopen(BASYX + "/submodels", timeout=3) as f:
            r["submodelos"] = [s["idShort"] for s in json.load(f)["result"]]
        sid = base64.urlsafe_b64encode(SM_OPER.encode()).decode().rstrip("=")
        with urllib.request.urlopen(f"{BASYX}/submodels/{sid}/$value", timeout=3) as f:
            v = json.load(f)
        r.update(ok=True, last_update=v.get("LastUpdate"), ciclos=v.get("CycleCount"))
    except Exception as e:
        r["erro"] = str(e)[:80]
    return r


def host():
    mem = {}
    with open("/proc/meminfo") as f:
        for l in f:
            k, v = l.split(":")
            mem[k] = int(v.split()[0])
    disco = shutil.disk_usage("/")
    try:
        with open("/sys/class/thermal/thermal_zone0/temp") as f:
            temp = round(int(f.read()) / 1000, 1)
    except Exception:
        temp = None
    fonte = ""
    for l in sh("chronyc", "-n", "sources").splitlines():
        if l.startswith("^*"):
            fonte = l.split()[1]
    ips = {}
    for l in sh("ip", "-br", "-4", "a").splitlines():
        p = l.split()
        if len(p) >= 3 and p[0] in ("eth0", "wlan0"):
            ips[p[0]] = p[2].split("/")[0]
    return {"nome": socket.gethostname(), "uptime_s": round(uptime_s()),
            "hora": time.strftime("%d/%m/%Y %H:%M:%S"), "ntp_fonte": fonte,
            "temp_c": temp, "carga": os.getloadavg()[0],
            "mem_usada_mb": round((mem["MemTotal"] - mem["MemAvailable"]) / 1024),
            "mem_total_mb": round(mem["MemTotal"] / 1024),
            "disco_livre_gb": round(disco.free / 1e9, 1),
            "disco_total_gb": round(disco.total / 1e9, 1), "ips": ips}


if __name__ == "__main__":
    print(json.dumps({"host": host(), "servicos": servicos(), "conteineres": conteineres(),
                      "broker": broker(), "aas": aas()}, ensure_ascii=False))
