#!/bin/bash
# stop.sh — Stop all DjangoWorkers services

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PIDS_DIR="$PROJECT_DIR/.service_pids"

echo -e "\n${BOLD}${BLUE}━━━  DjangoWorkers — Shutdown  ━━━${NC}"

if [ ! -d "$PIDS_DIR" ] || ! compgen -G "$PIDS_DIR/*.pid" > /dev/null 2>&1; then
    echo -e "${YELLOW}[WARN]${NC} No running services found."
    exit 0
fi

for pid_file in "$PIDS_DIR"/*.pid; do
    [ -f "$pid_file" ] || continue
    name=$(basename "$pid_file" .pid)
    pid=$(cat "$pid_file")
    echo -e "${CYAN}[INFO]${NC} Stopping $name (PID: $pid)..."
    if kill "$pid" 2>/dev/null; then
        echo -e "${GREEN}[OK]${NC}   $name stopped"
    else
        echo -e "${YELLOW}[WARN]${NC} $name was already stopped"
    fi
done

# Also kill any remaining celery.exe (spawned by Celery on Windows)
taskkill //F //IM celery.exe > /dev/null 2>&1 && echo -e "${GREEN}[OK]${NC}   celery.exe processes killed" || true

rm -rf "$PIDS_DIR"
echo -e "\n${GREEN}All services stopped.${NC}\n"
