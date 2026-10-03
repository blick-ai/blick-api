# reclassificar_tudo.ps1
# Reclassifica TODAS as capturas com o modelo novo (regra N>=2).
# Faz login, itera em lotes de 3, e reloga automaticamente se o token expirar.

$apiBase = "https://1uzo5w52jk.execute-api.us-east-1.amazonaws.com"
$email = "lucascrapino@gmail.com"
$senha = "BlickMaua2026!"
$tamanhoPagina = 3

function Login {
    $body = @{ email = $email; senha = $senha } | ConvertTo-Json
    $resp = Invoke-RestMethod -Uri "$apiBase/auth/login" -Method POST -ContentType "application/json" -Body $body
    return $resp.access_token
}

$token = Login
$pagina = 1
$totalPaginas = 1
$totalProcessadas = 0
$totalErros = 0

while ($pagina -le $totalPaginas) {
    try {
        $resultado = Invoke-RestMethod -Uri "$apiBase/capturas/reclassificar-todas?pagina=$pagina&tamanhoPagina=$tamanhoPagina" `
            -Method POST `
            -Headers @{ Authorization = "Bearer $token" }

        $totalPaginas = $resultado.totalPaginas
        $totalProcessadas += $resultado.processadas
        $totalErros += $resultado.erros

        Write-Host "Pagina $pagina de $totalPaginas - processadas: $($resultado.processadas), erros: $($resultado.erros)"
        $pagina++
    }
    catch {
        $status = $_.Exception.Response.StatusCode.value__
        if ($status -eq 401) {
            Write-Host "Token expirou, relogando..."
            $token = Login
        }
        else {
            Write-Host "Erro na pagina $pagina ($status) - aguardando 40s e tentando de novo..."
            Start-Sleep -Seconds 40
        }
    }
}

Write-Host "FIM. Total processadas: $totalProcessadas, total erros: $totalErros"
