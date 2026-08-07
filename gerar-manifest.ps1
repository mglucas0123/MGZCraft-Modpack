[CmdletBinding()]
param (
    [Parameter(Position = 0)]
    [string]$Message
)

$ErrorActionPreference = "Stop"
$Repo = "mglucas0123/MGZCraft-Modpack"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host " 🔄 Gerando manifest.json do Modpack" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

# 1. Executa o script de geracao do manifest
python update_index.py --repo $Repo

if ($LASTEXITCODE -ne 0) {
    Write-Host "`n❌ Erro ao executar update_index.py!" -ForegroundColor Red
    exit $LASTEXITCODE
}

Write-Host "`n✅ Manifest gerado com sucesso!" -ForegroundColor Green

# 2. Se a mensagem de commit foi passada como parametro
if (-not [string]::IsNullOrWhiteSpace($Message)) {
    Write-Host "`n🚀 Enviando para o GitHub..." -ForegroundColor Cyan
    git add -A
    git commit -m $Message
    git push
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "`n🎉 Modpack atualizado e enviado para o GitHub com sucesso!" -ForegroundColor Green
    }
    exit 0
}

# 3. Se nenhuma mensagem foi passada, mostra o status e pergunta se deseja subir
Write-Host "`n----------------------------------------" -ForegroundColor Yellow
Write-Host " Status atual do repositorio (Git):" -ForegroundColor Yellow
Write-Host "----------------------------------------" -ForegroundColor Yellow
git status --short

Write-Host ""
$resposta = Read-Host "Deseja fazer commit e push das alteracoes agora? (S/n)"

if ($resposta -eq "" -or $resposta -match "^[SsYy]") {
    $commitMsg = Read-Host "Digite a mensagem do commit (ou Pressione Enter para 'update: modpack')"
    if ([string]::IsNullOrWhiteSpace($commitMsg)) {
        $commitMsg = "update: modpack"
    }

    Write-Host "`n🚀 Enviando para o GitHub..." -ForegroundColor Cyan
    git add -A
    git commit -m $commitMsg
    git push

    if ($LASTEXITCODE -eq 0) {
        Write-Host "`n🎉 Modpack atualizado e enviado para o GitHub com sucesso!" -ForegroundColor Green
    }
} else {
    Write-Host "`ninfo: Manifest atualizado localmente. O envio para o Git foi ignorado." -ForegroundColor Gray
}
