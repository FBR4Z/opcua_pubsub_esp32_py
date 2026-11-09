# Fixa o IP da placa "Ethernet" do PC (cabo direto ao RPi 5) para o chrony do RPi sempre achar o PC.
# Rodar: powershell -ExecutionPolicy Bypass -File deploy\pc\fixar-ip-cabo.ps1  (pede UAC sozinho)

$admin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $admin) {
    Start-Process powershell -Verb RunAs -ArgumentList "-NoExit -ExecutionPolicy Bypass -File `"$PSCommandPath`""
    exit
}
$ErrorActionPreference = 'Stop'

$placa = 'Ethernet'
$ip    = '169.254.124.59'   # PC     (RPi 5 eth0 = 169.254.14.189)

# Sem gateway: a internet do PC continua pelo Wi-Fi de casa
netsh interface ipv4 set address name="$placa" source=static address=$ip mask=255.255.0.0
Start-Sleep 3
Get-NetIPAddress -InterfaceAlias $placa -AddressFamily IPv4 | Select-Object InterfaceAlias, IPAddress, PrefixOrigin
Test-Connection 169.254.14.189 -Count 2 | Select-Object Address, ResponseTime
Write-Host 'IP do cabo fixado.'
