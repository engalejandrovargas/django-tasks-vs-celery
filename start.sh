#!/bin/bash
# start.sh — Start all DjangoWorkers services, each in its own terminal window

set -e

# ── Colors ────────────────────────────────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

# ── Paths ─────────────────────────────────────────────────────────────────────
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_ACTIVATE="$PROJECT_DIR/myenv/Scripts/activate"
PIDS_DIR="$PROJECT_DIR/.service_pids"
ENV_FILE="$PROJECT_DIR/.env"
MINTTY="/usr/bin/mintty"

# ── Load .env ─────────────────────────────────────────────────────────────────
if [ -f "$ENV_FILE" ]; then
    export $(grep -v '^#' "$ENV_FILE" | xargs)
fi
DB_HOST="${DB_HOST:-localhost}"
DB_PORT="${DB_PORT:-5432}"
DB_NAME="${DB_NAME:-smart_meter_db}"
REDIS_URL="${REDIS_URL:-redis://localhost:6379/0}"

# ── Helpers ───────────────────────────────────────────────────────────────────
info()    { echo -e "${CYAN}[INFO]${NC} $1"; }
success() { echo -e "${GREEN}[OK]${NC}   $1"; }
warn()    { echo -e "${YELLOW}[WARN]${NC} $1"; }
error()   { echo -e "${RED}[ERR]${NC}  $1"; }
header()  { echo -e "\n${BOLD}${BLUE}$1${NC}"; }

# ── Guard: already running? ───────────────────────────────────────────────────
if [ -d "$PIDS_DIR" ] && compgen -G "$PIDS_DIR/*.pid" > /dev/null 2>&1; then
    warn "Services may already be running. Run ./stop.sh first."
    exit 1
fi

header "━━━  DjangoWorkers — Startup  ━━━"

# ── Activate virtualenv ───────────────────────────────────────────────────────
if [ ! -f "$VENV_ACTIVATE" ]; then
    error "Virtual environment not found: $VENV_ACTIVATE"
    error "Run: python -m venv myenv && myenv/Scripts/pip install -r requirements.txt"
    exit 1
fi
source "$VENV_ACTIVATE"
success "Virtual environment activated"

# ── Install / verify dependencies ─────────────────────────────────────────────
if ! python -c "import rest_framework" 2>/dev/null; then
    warn "Dependencies missing — running pip install -r requirements.txt ..."
    pip install -r "$PROJECT_DIR/requirements.txt" || {
        error "pip install failed."
        exit 1
    }
    success "Dependencies installed"
else
    success "Dependencies already installed"
fi

# ── Pre-flight: PostgreSQL ────────────────────────────────────────────────────
header "Pre-flight checks"
info "Checking PostgreSQL ($DB_HOST:$DB_PORT)..."
if python -c "
import psycopg2, os, sys
try:
    conn = psycopg2.connect(
        host=os.environ.get('DB_HOST','localhost'),
        port=os.environ.get('DB_PORT', 5432),
        dbname=os.environ.get('DB_NAME','smart_meter_db'),
        user=os.environ.get('DB_USER','postgres'),
        password=os.environ.get('DB_PASSWORD',''),
        connect_timeout=3
    )
    conn.close()
except Exception as e:
    sys.exit(1)
" 2>/dev/null; then
    success "PostgreSQL is reachable"
else
    error "Cannot connect to PostgreSQL at $DB_HOST:$DB_PORT/$DB_NAME"
    error "Make sure PostgreSQL is running before starting."
    exit 1
fi

# ── Pre-flight: Redis / Memurai ───────────────────────────────────────────────
info "Checking Redis ($REDIS_URL)..."
if python -c "
import redis, os, sys
try:
    r = redis.from_url(os.environ.get('REDIS_URL','redis://localhost:6379/0'), socket_connect_timeout=3)
    r.ping()
except Exception as e:
    sys.exit(1)
" 2>/dev/null; then
    success "Redis / Memurai is reachable"
    SKIP_CELERY=false
else
    warn "Redis not reachable — Celery and Flower will be skipped."
    SKIP_CELERY=true
fi

# ── Prepare PID directory ─────────────────────────────────────────────────────
rm -rf "$PIDS_DIR"
mkdir -p "$PIDS_DIR"

# ── Function: open service in a new mintty window ────────────────────────────
# Usage: open_window <window-title> <pid-name> <command>
open_window() {
    local title="$1"
    local pid_name="$2"
    local cmd="$3"

    info "Opening: $title"
    "$MINTTY" --title "$title" -e bash -c "
        cd '$PROJECT_DIR'
        source '$VENV_ACTIVATE'
        $cmd &
        echo \$! > '$PIDS_DIR/${pid_name}.pid'
        wait
        echo ''
        echo '[$title] Process exited. Press Enter to close...'
        read
    " &
    sleep 0.3
    success "$title — window opened"
}

# ── Kill any stale project processes ─────────────────────────────────────────
kill_stale() {
    # Kill all celery.exe instances
    taskkill //F //IM celery.exe > /dev/null 2>&1 && warn "Killed stale celery.exe processes" || true

    # Free ports
    for port in 8001 5555; do
        local pid
        pid=$(netstat -ano 2>/dev/null | awk "/:${port} .*LISTENING/{print \$NF}" | head -1)
        if [ -n "$pid" ]; then
            warn "Port $port in use (PID $pid) — killing it..."
            taskkill //PID "$pid" //F > /dev/null 2>&1 || true
        fi
    done
}

# ── Start services ────────────────────────────────────────────────────────────
header "Starting services"
cd "$PROJECT_DIR"

kill_stale

open_window "Django Server :8001"  "django"    "python manage.py runserver 8001"
open_window "Django Tasks Worker"  "db_worker" "python manage.py db_worker"

if [ "$SKIP_CELERY" != "true" ]; then
    open_window "Celery Worker"    "celery"    "celery -A config worker -l info --pool=solo"
    open_window "Flower :5555"     "flower"    "celery -A config flower --port=5555"
fi

# ── Summary ───────────────────────────────────────────────────────────────────
header "All services started"
echo -e "  ${BOLD}Comparison${NC}    http://localhost:8001/api/comparison/dashboard/"
echo -e "  ${BOLD}API${NC}           http://localhost:8001/api/"
echo -e "  ${BOLD}Swagger docs${NC}  http://localhost:8001/api/docs/"
echo -e "  ${BOLD}Django admin${NC}  http://localhost:8001/admin/"
if [ "$SKIP_CELERY" != "true" ]; then
    echo -e "  ${BOLD}Flower${NC}        http://localhost:5555/"
fi
echo ""
echo -e "  Stop → ${YELLOW}./stop.sh${NC}"
echo ""
