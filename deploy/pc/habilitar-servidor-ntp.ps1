# Liga o servidor NTP do Windows (w32time) para o RPi 5 acertar a hora pelo cabo.
# Rodar em PowerShell como Administrador:
#   powershell -ExecutionPolicy Bypass -File deploy\pc\habilitar-servidor-ntp.ps1
# Se nao estiver como Administrador, pede elevacao (UAC) e roda de novo numa janela nova.

$admin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $admin) {
    Start-Process powershell -Verb RunAs -ArgumentList "-NoExit -ExecutionPolicy Bypass -File `"$PSCommandPath`""
    exit
}
$ErrorActionPreference = 'Stop'

$w32 = 'HKLM:\SYSTEM\CurrentControlSet\Services\W32Time'
Set-ItemProperty "$w32\TimeProviders\NtpServer" -Name Enabled -Value 1
Set-ItemProperty "$w32\Config" -Name AnnounceFlags -Value 5   # sempre servidor de hora confiavel

Set-Service w32time -StartupType Automatic
Restart-Service w32time
# O proprio PC acerta a hora pela internet (sem isso ele fica em "Local CMOS Clock", dispersao 10 s)
w32tm /config /syncfromflags:manual /manualpeerlist:"a.ntp.br,0x9 time.windows.com,0x9" /reliable:yes /update | Out-Null
w32tm /resync /rediscover | Out-Null

# Firewall: NTP (UDP 123) e ping, so para a rede link-local do cabo
$rede = '169.254.0.0/16'
Get-NetFirewallRule -DisplayName 'Celula - *' -ErrorAction SilentlyContinue | Remove-NetFirewallRule
New-NetFirewallRule -DisplayName 'Celula - NTP servidor' -Direction Inbound -Protocol UDP -LocalPort 123 -RemoteAddress $rede -Action Allow -Profile Any | Out-Null
New-NetFirewallRule -DisplayName 'Celula - ping' -Direction Inbound -Protocol ICMPv4 -IcmpType 8 -RemoteAddress $rede -Action Allow -Profile Any | Out-Null

w32tm /query /configuration | Select-String 'NtpServer|Enabled|AnnounceFlags'
Start-Sleep 5
w32tm /query /status
Write-Host 'Servidor NTP ligado.'
