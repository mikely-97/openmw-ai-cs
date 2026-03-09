#!/usr/bin/env bash
# Build script for Jungle Troll Tribes standalone .omwgame
# Usage: bash build.sh [--clean]
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OMWTOOLS_DIR="$SCRIPT_DIR/../../omwtools"
RECORDS_DIR="$SCRIPT_DIR/records"
DB="$SCRIPT_DIR/jungle_troll_tribes.db"
OUTPUT="$SCRIPT_DIR/jungle_troll_tribes.omwgame"

# Clean previous build
if [[ "${1:-}" == "--clean" ]] || [[ -f "$DB" ]]; then
    rm -f "$DB"
    echo "[build] Cleaned previous database."
fi

cd "$OMWTOOLS_DIR"

echo ""
echo "============================================================"
echo "  Jungle Troll Tribes — omwtools build pipeline"
echo "============================================================"
echo ""

# Initialize the database schema and create mod entry (id=1)
echo "[init] Creating mod entry in database ..."
poetry run omw --db "$DB" query "INSERT INTO mods (id, filename, file_type, format_version, author, description, record_count) VALUES (1, 'jungle_troll_tribes.omwgame', 0, 0, 'Tribal Council', 'Jungle Troll Tribes - Survival strategy on the Jungle Isle', 300)"

# Import all records in order — fully standalone, no template.omwgame dependency
for f in "$RECORDS_DIR"/[0-9]*.json; do
    fname=$(basename "$f")
    echo "[import] $fname ..."
    poetry run omw --db "$DB" import "$f" --mod-id 1
done

echo ""
echo "[info] Database contents:"
poetry run omw --db "$DB" info

echo ""
echo "[validate] Running validation ..."
poetry run omw --db "$DB" validate --mod-id 1 || true

echo ""
echo "[write] Writing binary game file ..."
poetry run omw --db "$DB" write --output "$OUTPUT" --mod-id 1

echo ""
echo "[dump] Sample weapon records:"
poetry run omw --db "$DB" dump --rec-type WEAP | python3 -c "
import sys, json
data = json.load(sys.stdin)
for r in data[:3]:
    print(f'  {r[\"record_id\"]:30s} {r[\"name\"]:25s} type={r[\"weap_type\"]}')
" 2>/dev/null || poetry run omw --db "$DB" dump --rec-type WEAP

echo ""
echo "[dump] NPC records:"
poetry run omw --db "$DB" dump --rec-type NPC_ | python3 -c "
import sys, json
data = json.load(sys.stdin)
for r in data:
    print(f'  {r[\"record_id\"]:30s} {r[\"name\"]:30s} faction={r[\"faction\"]}')
" 2>/dev/null || poetry run omw --db "$DB" dump --rec-type NPC_

echo ""
echo "[dump] Spell records:"
poetry run omw --db "$DB" dump --rec-type SPEL | python3 -c "
import sys, json
data = json.load(sys.stdin)
for r in data:
    print(f'  {r[\"record_id\"]:30s} {r[\"name\"]:30s} cost={r[\"cost\"]} type={r[\"spell_type\"]}')
" 2>/dev/null || poetry run omw --db "$DB" dump --rec-type SPEL

echo ""
echo "[done] ============================================"
ls -lh "$OUTPUT"
echo "[done] Game written: $OUTPUT"
echo "[done] ============================================"
echo ""
echo "To load in OpenMW (standalone — no Morrowind.esm or template required):"
echo "  In openmw.cfg set:"
echo "       content=jungle_troll_tribes.omwgame"
echo "  Then start OpenMW with: --skip-menu --new-game"
