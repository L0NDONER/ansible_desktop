#!/usr/bin/env bash
# minty_clean.sh - Organize Ansible/home-lab clutter safely
# Protects: ansible.cfg, inventory/, .git/, README*, *.service, *.timer, etc. in ROOT
# Usage: ./minty_clean.sh [--apply] [--recursive]
set -euo pipefail

DRY_RUN=true
RECURSIVE=false

while [[ $# -gt 0 ]]; do
    case "$1" in
        --apply)          DRY_RUN=false; shift ;;
        --recursive)      RECURSIVE=true; shift ;;
        *)                echo "Unknown flag: $1"; exit 1 ;;
    esac
done

if [[ "$DRY_RUN" == "false" ]]; then
    echo "⚠️  APPLY MODE: Files WILL be moved. Ctrl+C in next 5 seconds if unsure."
    sleep 5
else
    echo "🔍 DRY RUN: No changes made. Use --apply to execute."
fi

TARGET_DIRS=("playbooks" "backups" "commander")  # removed systemd/ since units stay in root

echo "→ Creating target directories (if needed)..."
for dir in "${TARGET_DIRS[@]}"; do
    if [[ ! -d "$dir" ]]; then
        if [[ "$DRY_RUN" == "false" ]]; then
            mkdir -p "$dir"
            echo "Created: $dir/"
        else
            echo "[Plan] Create: $dir/"
        fi
    else
        echo "Exists: $dir/"
    fi
done

# ────────────────────────────────────────────────
# IMPORTANT: Files / dirs to NEVER move (keep in ROOT)
EXCLUDE_PATTERNS=(
    "ansible.cfg"
    "inventory"
    "inventory/"
    ".git"
    ".git/"
    "README*"
    "group_vars"
    "group_vars/"
    "host_vars"
    "host_vars/"
    "roles"
    "roles/"
    ".gitignore"
    ".ansible-lint"
    "requirements.yml"
    "requirements.txt"
    ".env"
    "docker-compose.*"
    # ── Systemd units & related (keep in root) ──
    "*.service"
    "*.timer"
    "*.override"       # drop-in style if you ever use them in root
    "*.target"         # optional, if you have custom targets
    # Add more if needed, e.g. "my-custom*.service"
)

# Helper: check if path matches any exclude pattern
should_skip() {
    local path="$1"
    for excl in "${EXCLUDE_PATTERNS[@]}"; do
        if [[ "$excl" == */ ]]; then
            excl="${excl%/}"
            if [[ "$path" == ./"$excl" || "$path" == ./"$excl"/* ]]; then
                return 0  # skip (dir or contents)
            fi
        else
            # glob-style match for files (e.g. *.service)
            if [[ "$(basename "$path")" == $excl ]]; then
                return 0  # skip
            fi
        fi
    done
    return 1  # do NOT skip
}

move_files() {
    local pattern="$1"
    local dest="$2"
    local find_opts=()

    if [[ "$RECURSIVE" == "true" ]]; then
        find_opts=(-type f)
    else
        find_opts=(-maxdepth 1 -type f)
    fi

    find . "${find_opts[@]}" -name "$pattern" -print0 | while IFS= read -r -d '' file; do
        rel_file="./${file#./}"

        if should_skip "$rel_file"; then
            echo "[SKIP] Protected root item: $rel_file"
            continue
        fi

        if [[ "$rel_file" == ./"$dest"/* ]]; then
            continue
        fi

        target="$dest/$(basename "$file")"

        if [[ -e "$target" ]]; then
            echo "⚠️  Conflict: $target already exists → skipping $rel_file"
            continue
        fi

        if [[ "$DRY_RUN" == "false" ]]; then
            mv -v "$file" "$target"
        else
            echo "[Plan] Move → $rel_file  →  $target"
        fi
    done
}

echo "→ Moving matching files (skipping protected root items)..."

# Ansible playbooks (only .yml / .yaml go to playbooks/)
move_files "*.yml"      "playbooks"
move_files "*.yaml"     "playbooks"

# Backups & old files
move_files "*.backup"   "backups"
move_files "*.bak"      "backups"
move_files "*.save"     "backups"
move_files "*.old"      "backups"
move_files "*.orig"     "backups"

# Optional: commander (scripts, wrappers, tools?)
# move_files "*.sh"       "commander"
# move_files "minty_*"    "commander"

echo ""
echo "✅ Cleanup complete."
if [[ "$DRY_RUN" == "true" ]]; then
    echo "Run again with --apply to actually move files."
    echo "Use --recursive to also clean inside subdirectories (careful!)."
fi
