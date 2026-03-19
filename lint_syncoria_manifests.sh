#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

export PYTHONPATH=.

mapfile -t files < <(find . -type f -name "__manifest__.py" | while read -r file; do
    module_dir="$(basename "$(dirname "$file")")"
    if [[ "$module_dir" == syncoria* ]]; then
        printf '%s\n' "$file"
    fi
done)

if [ "${#files[@]}" -eq 0 ]; then
    echo "No syncoria* module manifests found."
    exit 0
fi

echo "Linting these manifest files:"
for file in "${files[@]}"; do
    echo " - $file"
done

python -m pylint --rcfile=.pylintrc --score=n "${files[@]}"