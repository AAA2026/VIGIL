param(
    [switch]$Rebuild
)

$composeArgs = "-f", "config/docker-compose.prod.yml"
if ($Rebuild) {
    docker compose @composeArgs up -d --build
} else {
    docker compose @composeArgs up -d
}
