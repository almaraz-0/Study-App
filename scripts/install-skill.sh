#!/usr/bin/env bash
# Link the /study skill into ~/.claude/skills so it works from any Claude Code chat.
set -euo pipefail

repo="$(cd "$(dirname "$0")/.." && pwd)"
target="$HOME/.claude/skills/study"

mkdir -p "$HOME/.claude/skills"
if [ -e "$target" ] && [ ! -L "$target" ]; then
  echo "Refusing: $target exists and is not a symlink. Move it aside and re-run." >&2
  exit 1
fi
ln -sfn "$repo/skills/study" "$target"
echo "Linked $target -> $repo/skills/study"
