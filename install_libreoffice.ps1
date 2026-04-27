# Script para instalar LibreOffice
# Descarga e instala LibreOffice silenciosamente

$downloadUrl = "https://www.libreoffice.org/donate/dl/win-x86_64/24.8.0/en-US/LibreOffice_24.8.0_Win_x86-64.msi"
$installerPath = "$env:TEMP\LibreOffice.msi"

Write-Host "Descargando LibreOffice..."
Invoke-WebRequest -Uri $downloadUrl -OutFile $installerPath

Write-Host "Instalando LibreOffice..."
Start-Process msiexec.exe -ArgumentList "/i $installerPath /quiet /norestart" -Wait

Write-Host "LibreOffice instalado. Reinicia la aplicación."