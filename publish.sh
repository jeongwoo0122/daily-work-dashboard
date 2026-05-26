#!/usr/bin/env bash
# 빌드된 docs/index.html을 GitHub Pages 호스팅 repo로 push합니다.
# build.py 직후에 실행하세요.
#
# 사용:
#   bash publish.sh
#
# 사전 조건:
#   - 이 폴더(daily-work-dashboard)가 Tesser/daily-work-dashboard repo의 clone이어야 함
#     (또는 git remote가 그 repo로 설정되어 있어야 함)
#   - gh CLI로 인증되어 있거나, SSH key가 등록되어 있어야 함
#
# 동작:
#   1. 변경사항 없으면 그냥 종료 (조용히)
#   2. 변경사항 있으면 docs/index.html만 add → commit → push

set -euo pipefail

DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$DIR"

# git repo가 아니면 친절히 안내
if ! git rev-parse --git-dir >/dev/null 2>&1; then
  echo "ERROR: $DIR 가 git repo가 아닙니다." >&2
  echo "  최초 1회 셋업:" >&2
  echo "    cd \"$DIR\"" >&2
  echo "    git init -b main" >&2
  echo "    git remote add origin git@github.com:Tesser/daily-work-dashboard.git" >&2
  echo "    git add . && git commit -m 'Initial' && git push -u origin main" >&2
  exit 1
fi

# 변경사항 없으면 skip
if git diff --quiet docs/index.html 2>/dev/null && git diff --cached --quiet docs/index.html 2>/dev/null; then
  # 새 파일일 가능성도 체크
  if ! git ls-files --others --exclude-standard docs/index.html | grep -q .; then
    echo "변경사항 없음 — push 생략."
    exit 0
  fi
fi

TODAY="$(date '+%Y-%m-%d %H:%M %Z')"

git add docs/index.html
git commit -m "chore: daily dashboard refresh $TODAY" --no-verify

# upstream이 설정되어 있으면 그대로, 없으면 origin/main 가정
if git rev-parse --abbrev-ref --symbolic-full-name '@{u}' >/dev/null 2>&1; then
  git push
else
  git push -u origin main
fi

echo "push 완료 → GitHub Pages가 1~2분 내 새 페이지를 배포합니다."
