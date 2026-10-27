#!/usr/bin/env bash
# Install the ontology-games demo end to end: database, Parquet data, semantic views and agents,
# Business Ontology, and the compare web app.
#
# Each step is a numbered file in install/ (or a command) and runs in order:
#   00 generate the SQL files from their sources    04 Business Ontology (build or refresh)
#   01 database, schemas, stage, file format        05 web app role and grants   
#   02 load data (tables, COPY INTO, views, DTs)    06 start the web app (foreground; Ctrl-C stops it)
#   03 semantic views and agents (baseline, BON, router demo)
#
# Usage: ./install.sh [--from NN] [--only NN] [--list]
#   --from NN   resume at step NN        --list   show steps and what has completed
#   --only NN   run just step NN
# Connection: SNOWFLAKE_CONNECTION_NAME (default ONTOLOGY_DEMO_CONN in ~/.snowflake/connections.toml).
# Progress is kept in .install_state; delete it to start over.
# No data is generated: everything loads from data/*.parquet (see documentation/data-generation.md).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"
CONN="${SNOWFLAKE_CONNECTION_NAME:-ONTOLOGY_DEMO_CONN}"
STATE="$ROOT/.install_state"

STEPS=(00 01 02 03 04 05 06)
title() {  # bash 3.2 (macOS default) has no associative arrays
  case "$1" in
    00) echo "Generate install SQL from sources" ;;  01) echo "Database, schemas, stage" ;;
    02) echo "Load data from Parquet" ;;             03) echo "Semantic views and agents" ;;
    04) echo "Business Ontology" ;;                  05) echo "Web app role" ;;
    06) echo "Start web app" ;;
  esac
}

FROM=00; ONLY=""
while (($#)); do
  case "$1" in
    --from) FROM="$2"; shift 2 ;;
    --only) ONLY="$2"; shift 2 ;;
    --list)
      for s in "${STEPS[@]}"; do
        mark=" "; grep -qx "DONE_$s=1" "$STATE" 2>/dev/null && mark="x"
        printf "[%s] %s  %s\n" "$mark" "$s" "$(title "$s")"
      done
      exit 0 ;;
    *) echo "Unknown option: $1 (see the header of install.sh)" >&2; exit 1 ;;
  esac
done

state_set() {  # state_set KEY VALUE
  touch "$STATE"
  grep -v "^$1=" "$STATE" > "$STATE.tmp" || true
  echo "$1=$2" >> "$STATE.tmp"
  mv "$STATE.tmp" "$STATE"
}

sql_file() {  # sql_file install/NN-name.sql
  snow sql -c "$CONN" --enable-templating NONE -f "$1"
}

# Reads the last result set of a `snow sql --format json` call and prints one column.
json_col() {
  python3 -c '
import json, sys
data = json.load(sys.stdin)
rows = data[-1] if data and isinstance(data[0], list) else data
print(rows[0].get(sys.argv[1], "") if rows else "")' "$1"
}

step_file() { ls install/"$1"-*.sql 2>/dev/null | head -1; }

run_step() {
  local s="$1"
  echo; echo "==> $s $(title "$s")"
  case "$s" in
    00) python3 scripts/generate_install_sql.py ;;
    04)
      # The domain calls are not idempotent: build on a fresh account, otherwise refresh in place.
      local domains
      domains="$(snow sql -c "$CONN" --enable-templating NONE --format json \
        -q "SELECT PARSE_JSON(SYSTEM\$GET_GLOSSARY_SUMMARY()):domainCount::INT AS N" | json_col N)"
      if [[ -z "$domains" || "$domains" == "0" ]]; then
        echo "  no ontology domains yet; building"
        sql_file install/04a-build-ontology.sql
      else
        echo "  $domains ontology domains exist; refreshing descriptions and formulas in place"
        sql_file install/04b-refresh-ontology.sql
      fi ;;
    05)
      sql_file app/sql/01_app_role.sql ;;
    06)
      bash app/dev.sh ;;  # creates app/.venv and installs the backend requirements
    *) sql_file "$(step_file "$s")" ;;
  esac
  state_set "DONE_$s" 1
}

echo "Connection: $CONN"
snow connection test -c "$CONN" > /dev/null || {
  echo "Connection '$CONN' failed. Add it to ~/.snowflake/connections.toml (see README) or set SNOWFLAKE_CONNECTION_NAME." >&2
  exit 1; }

for s in "${STEPS[@]}"; do
  if [[ -n "$ONLY" ]]; then [[ "$s" == "$ONLY" ]] && run_step "$s"; continue; fi
  [[ "$s" < "$FROM" ]] && continue
  run_step "$s"
done
echo; echo "Done."
