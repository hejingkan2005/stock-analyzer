param(
    [Parameter(Mandatory = $true)]
    [string]$SubscriptionId,

    [Parameter(Mandatory = $false)]
    [string]$ResourceGroup = "rg-stock-analyzer",

    [Parameter(Mandatory = $false)]
    [string]$Location = "eastus",

    [Parameter(Mandatory = $false)]
    [string]$PlanName = "asp-stock-analyzer-linux",

    [Parameter(Mandatory = $false)]
    [string]$AppName = ""
)

$ErrorActionPreference = "Stop"

if (-not $AppName) {
    $suffix = Get-Random -Minimum 10000 -Maximum 99999
    $AppName = "stockanalyzer$suffix"
}

Write-Host "Using app name: $AppName"

az account set --subscription $SubscriptionId | Out-Null

$pkgDir = ".azure_deploy_pkg"
$zipPath = "deploy.zip"
if (Test-Path $pkgDir) { Remove-Item $pkgDir -Recurse -Force }
if (Test-Path $zipPath) { Remove-Item $zipPath -Force }

New-Item -ItemType Directory -Path $pkgDir | Out-Null
Copy-Item app.py, requirements.txt, README.md $pkgDir
Copy-Item assets $pkgDir -Recurse
Compress-Archive -Path "$pkgDir\*" -DestinationPath $zipPath -Force

az group create -n $ResourceGroup -l $Location | Out-Null
az appservice plan create -n $PlanName -g $ResourceGroup --is-linux --sku B1 | Out-Null
az webapp create -g $ResourceGroup -p $PlanName -n $AppName --runtime "PYTHON:3.12" | Out-Null
az webapp config appsettings set -g $ResourceGroup -n $AppName --settings SCM_DO_BUILD_DURING_DEPLOYMENT=true | Out-Null
az webapp config set -g $ResourceGroup -n $AppName --startup-file "gunicorn --bind=0.0.0.0:\$PORT --timeout 600 app:server" | Out-Null
az webapp deploy -g $ResourceGroup -n $AppName --src-path $zipPath --type zip | Out-Null

Write-Host "Deployment completed: https://$AppName.azurewebsites.net"
