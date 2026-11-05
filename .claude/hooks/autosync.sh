#!/usr/bin/env bash
# Two-machine auto-sync, called by the hooks in .claude/settings.json:
#   start = SessionStart, stop = Stop (async), end = SessionEnd.
# For this repo and the private sibling repo ../shuron-private:
#   commit local changes -> pull --rebase -> push,
#   and copy the private single files (CLAUDE.md etc.) out of / into place.
# Problems are written to .git/autosync-warnings and shown at the next session start.
set -u
EVENT="${1:-manual}"
PROJ="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
PRIV="$(cd "$PROJ/.." && pwd)/shuron-private"
UHOME="$(cygpath -u "${USERPROFILE:-$HOME}" 2>/dev/null || echo "$HOME")"
HOST="${COMPUTERNAME:-$(hostname)}"
MAX_BYTES=$((50 * 1024 * 1024))
LOCK="$PROJ/.git/autosync.lock.d"
OUT=()

say() { OUT+=("$1"); }
log() { echo "$(date '+%F %T') [$EVENT] $*" >> "$PROJ/.git/autosync.log"; }
warn() { # $1 = repo, rest = message
  local r="$1"; shift
  echo "$(date '+%m-%d %H:%M') $HOST [$EVENT] $*" >> "$r/.git/autosync-warnings"
  log "WARN $*"
}

file_map() {
  cat <<EOF
files/project/CLAUDE.md|$PROJ/CLAUDE.md
files/project/AGENTS.md|$PROJ/AGENTS.md
files/project/settings.local.json|$PROJ/.claude/settings.local.json
files/user/CLAUDE.md|$UHOME/.claude/CLAUDE.md
files/user/settings.json|$UHOME/.claude/settings.json
EOF
}

copy_out() {
  while IFS='|' read -r rel loc; do
    [ -f "$loc" ] || continue
    cmp -s "$loc" "$PRIV/$rel" || { mkdir -p "$(dirname "$PRIV/$rel")"; cp "$loc" "$PRIV/$rel"; }
  done < <(file_map)
}

copy_in() {
  local changed=""
  while IFS='|' read -r rel loc; do
    [ -f "$PRIV/$rel" ] || continue
    if ! cmp -s "$PRIV/$rel" "$loc"; then
      mkdir -p "$(dirname "$loc")"; cp "$PRIV/$rel" "$loc"; changed="$changed ${rel#files/}"
    fi
  done < <(file_map)
  [ -n "$changed" ] && say "另一台机器改过这些文件，已更新到本机:$changed（CLAUDE.md 和设置下次开会话才生效）"
}

sync_repo() { # $1 = repo path, $2 = label
  local r="$1" label="$2" big=""
  cd "$r" || return 1
  if [ -e .git/index.lock ] || [ -d .git/rebase-merge ] || [ -d .git/rebase-apply ] || [ -f .git/MERGE_HEAD ]; then
    warn "$r" "$label: git 正被占用或停在冲突中，这次没有同步"; return 1
  fi
  git add -A >/dev/null 2>&1
  # GitHub rejects files over 100 MB; keep anything over 50 MB out and say so
  while IFS= read -r -d '' f; do
    if [ -f "$f" ] && [ "$(stat -c %s "$f")" -gt "$MAX_BYTES" ]; then
      git reset -q -- "$f"; printf '/%s\n' "$f" >> .git/info/exclude; big="$big $f"
    fi
  done < <(git diff --cached --name-only -z --diff-filter=AM)
  [ -n "$big" ] && warn "$r" "$label: 这些文件超过 50 MB，没有提交，只留在本机:$big"
  if ! git diff --cached --quiet; then
    git commit -q -m "auto-sync from $HOST ($EVENT)" >/dev/null 2>&1 || { warn "$r" "$label: 提交失败"; return 1; }
  fi
  if ! git pull -q --rebase --autostash >/dev/null 2>&1; then
    git rebase --abort >/dev/null 2>&1
    warn "$r" "$label: 拉取失败（断网，或两台机器改了同一个文件）。本机改动已提交在本地，还没推送"
    return 1
  fi
  if [ -n "$(git rev-list '@{u}..HEAD' 2>/dev/null)" ]; then
    git push -q >/dev/null 2>&1 || { warn "$r" "$label: 推送失败"; return 1; }
  fi
  log "$label ok $(git rev-parse --short HEAD)"
  return 0
}

acquire() {
  local i
  for i in $(seq 1 90); do
    mkdir "$LOCK" 2>/dev/null && return 0
    [ -n "$(find "$LOCK" -maxdepth 0 -mmin +15 2>/dev/null)" ] && rmdir "$LOCK" 2>/dev/null
    sleep 1
  done
  return 1
}

acquire || { log "lock busy, skipped"; exit 0; }
trap 'rmdir "$LOCK" 2>/dev/null' EXIT

if [ "$EVENT" = start ]; then
  for r in "$PRIV" "$PROJ"; do
    if [ -s "$r/.git/autosync-warnings" ]; then
      while IFS= read -r line; do say "上次同步的问题：$line"; done < "$r/.git/autosync-warnings"
      rm -f "$r/.git/autosync-warnings"
    fi
  done
fi

PRIV_OK=skip
if [ -d "$PRIV/.git" ]; then
  [ -f "$PRIV/.git/autosync-initialized" ] && copy_out
  if sync_repo "$PRIV" "shuron-private"; then PRIV_OK=ok; else PRIV_OK=fail; fi
  copy_in
  touch "$PRIV/.git/autosync-initialized"
else
  say "没找到 $PRIV，私有文件（CLAUDE.md、记忆等）没有同步"
fi
if sync_repo "$PROJ" "shuron"; then PROJ_OK=ok; else PROJ_OK=fail; fi

if [ "$EVENT" = start ]; then
  for r in "$PRIV" "$PROJ"; do
    if [ -s "$r/.git/autosync-warnings" ]; then
      while IFS= read -r line; do say "同步问题：$line"; done < "$r/.git/autosync-warnings"
      rm -f "$r/.git/autosync-warnings"
    fi
  done
  status="自动同步（$HOST）：shuron $([ $PROJ_OK = ok ] && echo 已与 GitHub 一致 || echo 失败)"
  [ $PRIV_OK != skip ] && status="$status；shuron-private $([ $PRIV_OK = ok ] && echo 已与 GitHub 一致 || echo 失败)"
  echo "$status"
  for m in "${OUT[@]+"${OUT[@]}"}"; do echo "$m"; done
  [ $PROJ_OK = ok ] && [ $PRIV_OK != fail ] || echo "请在回复开头告诉用户同步出了问题，并按上面的提示处理。"
fi
exit 0
