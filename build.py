#!/usr/bin/env python3
"""
오늘의 작업 대시보드 빌더.

config.yml에 정의된 repo 목록을 순회하며 GitHub API에서 다음을 수집:
- 오늘 머지된 PR
- 현재 열려 있는 PR (open + draft)
- 오늘 성공한 deploy/release 워크플로우 run

template.html (Jinja2)에 렌더해서 docs/index.html로 출력합니다.
빌드 요약은 build_summary.json으로도 저장 (Slack 알림에서 사용).

환경 변수:
  GITHUB_TOKEN  - GitHub PAT (private repo 읽기 권한 필수)
  GITHUB_REPO   - (선택) Pages 호스팅용 자기 자신의 owner/repo. 출력 URL 계산에 사용.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable

import yaml
from dateutil import parser as dateparser
from github import Github, Auth
from github.GithubException import GithubException
from jinja2 import Environment, FileSystemLoader, select_autoescape

ROOT = Path(__file__).resolve().parent
TEMPLATE_PATH = ROOT / "template.html"
OUTPUT_PATH = ROOT / "docs" / "index.html"
SUMMARY_PATH = ROOT / "build_summary.json"
CONFIG_PATH = ROOT / "config.yml"

KST = timezone(timedelta(hours=9))

# ---------------------------------------------------------------------------
# SVG icons (inline)
# ---------------------------------------------------------------------------

ICON_OPEN_PR = (
    '<svg viewBox="0 0 16 16" fill="currentColor">'
    '<path d="M1.5 3.25a2.25 2.25 0 1 1 3 2.122v5.256a2.251 2.251 0 1 1-1.5 0V5.372A2.25 2.25 0 0 1 1.5 3.25Zm5.677-.177L9.573.677A.25.25 0 0 1 10 .854V2.5h1A2.5 2.5 0 0 1 13.5 5v5.628a2.251 2.251 0 1 1-1.5 0V5a1 1 0 0 0-1-1h-1v1.646a.25.25 0 0 1-.427.177L7.177 3.427a.25.25 0 0 1 0-.354ZM3.75 2.5a.75.75 0 1 0 0 1.5.75.75 0 0 0 0-1.5Zm0 9.5a.75.75 0 1 0 0 1.5.75.75 0 0 0 0-1.5Zm8.25.75a.75.75 0 1 0 1.5 0 .75.75 0 0 0-1.5 0Z"/>'
    "</svg>"
)
ICON_DRAFT_PR = (
    '<svg viewBox="0 0 16 16" fill="currentColor">'
    '<path d="M3.25 1A2.25 2.25 0 0 1 4 5.372v5.256a2.251 2.251 0 1 1-1.5 0V5.372A2.251 2.251 0 0 1 3.25 1Zm9.5 14a2.25 2.25 0 1 1 0-4.5 2.25 2.25 0 0 1 0 4.5ZM2.5 3.25a.75.75 0 1 0 1.5 0 .75.75 0 0 0-1.5 0ZM3.25 12a.75.75 0 1 0 0 1.5.75.75 0 0 0 0-1.5Zm9.5.75a.75.75 0 1 0 1.5 0 .75.75 0 0 0-1.5 0ZM14 7.5a1 1 0 1 1-2 0 1 1 0 0 1 2 0Zm0-3.5a1 1 0 1 1-2 0 1 1 0 0 1 2 0Zm-3.5-2.5a1 1 0 1 1-2 0 1 1 0 0 1 2 0Z"/>'
    "</svg>"
)
ICON_MERGED_PR = (
    '<svg viewBox="0 0 16 16" fill="currentColor">'
    '<path d="M5.45 5.154A4.25 4.25 0 0 0 9.25 7.5h1.378a2.251 2.251 0 1 1 0 1.5H9.25A5.734 5.734 0 0 1 5 7.123v3.505a2.25 2.25 0 1 1-1.5 0V5.372a2.25 2.25 0 1 1 1.95-.218ZM4.25 13.75a.75.75 0 1 0 0-1.5.75.75 0 0 0 0 1.5Zm8.5-4.5a.75.75 0 1 0 0-1.5.75.75 0 0 0 0 1.5ZM5 3.25a.75.75 0 1 0 0 .005Z"/>'
    "</svg>"
)
ICON_DEPLOY = (
    '<svg viewBox="0 0 16 16" fill="currentColor">'
    '<path d="M1 7.775V2.75C1 1.784 1.784 1 2.75 1h5.025c.464 0 .91.184 1.238.513l6.25 6.25a1.75 1.75 0 0 1 0 2.474l-5.026 5.026a1.75 1.75 0 0 1-2.474 0l-6.25-6.25A1.752 1.752 0 0 1 1 7.775Zm1.5 0c0 .066.026.13.073.177l6.25 6.25a.25.25 0 0 0 .354 0l5.025-5.025a.25.25 0 0 0 0-.354l-6.25-6.25a.25.25 0 0 0-.177-.073H2.75a.25.25 0 0 0-.25.25ZM6 5a1 1 0 1 1 0 2 1 1 0 0 1 0-2Z"/>'
    "</svg>"
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

CONVENTIONAL_RE = re.compile(
    r"^(?P<type>feat|fix|chore|refactor|perf|design|i18n|security|infra|polish|release|docs|test|style|build|ci|revert)"
    r"(?:\([^)]+\))?(?:!)?:",
    re.IGNORECASE,
)

# 흔한 issue tracker prefix (없으면 그냥 비워둠)
LINEAR_ISSUE_RE = re.compile(r"\b([A-Z]{2,5}-\d+)\b")


def short_repo(full: str) -> str:
    return full.split("/", 1)[1] if "/" in full else full


def initial(name: str) -> str:
    if not name:
        return "?"
    return name[0].upper()


def color_idx_for(handle: str, n_colors: int = 7) -> int:
    if not handle:
        return 0
    return sum(ord(c) for c in handle) % n_colors


def infer_labels(title: str, branch: str, gh_labels: Iterable[str], keyword_map: dict[str, list[str]]) -> list[str]:
    """제목, 브랜치명, GitHub label에서 분류 라벨을 추론."""
    out: list[str] = []
    seen: set[str] = set()
    blob = " ".join(filter(None, [title or "", branch or "", " ".join(gh_labels)])).lower()

    # Conventional commit prefix가 있으면 그것이 1순위
    m = CONVENTIONAL_RE.match((title or "").strip())
    if m:
        t = m.group("type").lower()
        if t in keyword_map and t not in seen:
            out.append(t)
            seen.add(t)

    for label, keywords in keyword_map.items():
        if label in seen:
            continue
        for kw in keywords:
            if kw.lower() in blob:
                out.append(label)
                seen.add(label)
                break
    return out[:3]  # 시각적으로 너무 많아지면 3개 컷


def time_display(dt: datetime) -> str:
    """오늘이면 HH:MM KST, 어제면 '어제 열림', 그 외엔 'N일 전 열림'."""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    local = dt.astimezone(KST)
    today_local = datetime.now(KST).date()
    delta_days = (today_local - local.date()).days
    if delta_days <= 0:
        return f"{local.strftime('%H:%M')} KST"
    if delta_days == 1:
        return "어제 열림"
    return f"{delta_days}일 전 열림"


def extract_linear(text: str) -> dict | None:
    """본문/제목/브랜치에서 ENG-123 류 ID를 찾아 Linear URL 매핑.
    매핑이 없으면 None."""
    if not text:
        return None
    m = LINEAR_ISSUE_RE.search(text)
    if not m:
        return None
    issue_id = m.group(1)
    workspace = os.environ.get("LINEAR_WORKSPACE", "").strip()
    if not workspace:
        return None  # workspace 없으면 링크 생성 못 함
    return {
        "id": issue_id,
        "url": f"https://linear.app/{workspace}/issue/{issue_id}",
    }


def body_bullets(body: str | None, max_bullets: int = 3) -> list[str]:
    """PR 본문에서 첫 줄들 또는 - / * 불릿을 추출."""
    if not body:
        return []
    lines = [ln.strip() for ln in body.splitlines()]
    # 1) 마크다운 불릿 라인 우선
    bullets = [re.sub(r"^[-*+]\s+", "", ln) for ln in lines if re.match(r"^[-*+]\s+", ln)]
    if bullets:
        # HTML 태그 / 매크로 제거
        return [strip_md(b) for b in bullets[:max_bullets] if b][:max_bullets]
    # 2) 첫 번째 비어있지 않은 문단을 줄 단위로 잘라서 사용
    para: list[str] = []
    for ln in lines:
        if not ln:
            if para:
                break
            continue
        if ln.startswith("#"):  # 헤더 제거
            continue
        if ln.startswith("<!--"):  # 코멘트 스킵
            continue
        para.append(strip_md(ln))
        if len(para) >= max_bullets:
            break
    return para[:max_bullets]


def strip_md(s: str) -> str:
    s = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", s)  # [text](url) → text
    s = re.sub(r"`([^`]+)`", r"\1", s)
    s = re.sub(r"\*\*([^*]+)\*\*", r"\1", s)
    s = re.sub(r"\*([^*]+)\*", r"\1", s)
    return s.strip()


# ---------------------------------------------------------------------------
# Data fetch
# ---------------------------------------------------------------------------

@dataclass
class FetchedItem:
    section: str  # 'deployed' | 'merged' | 'open'
    sort_key: float  # epoch seconds for stable ordering
    payload: dict[str, Any]


def fetch_repo(gh: Github, full: str, cfg: dict, today_start_utc: datetime, today_end_utc: datetime) -> list[FetchedItem]:
    items: list[FetchedItem] = []
    print(f"  · {full}", flush=True)
    repo = gh.get_repo(full)
    short = short_repo(full)
    keyword_map = cfg.get("label_keywords", {})

    # ---- 머지된 PR (오늘) ----
    try:
        # closed PR을 최신순으로 페이지네이션, 머지된 것만 필터
        closed = repo.get_pulls(state="closed", sort="updated", direction="desc")
        for pr in closed[:50]:  # 최근 50개만 본다 (성능)
            if pr.merged_at is None:
                continue
            merged_utc = pr.merged_at.replace(tzinfo=timezone.utc) if pr.merged_at.tzinfo is None else pr.merged_at
            if merged_utc < today_start_utc:
                break  # 정렬되어 있으니 종료
            if merged_utc > today_end_utc:
                continue
            gh_labels = [lbl.name for lbl in pr.labels]
            labels = infer_labels(pr.title, pr.head.ref if pr.head else "", gh_labels, keyword_map)
            author = pr.user
            payload = {
                "url": pr.html_url,
                "title": pr.title,
                "id_display": f"#{pr.number}",
                "status_class": "merged",
                "status_svg": ICON_MERGED_PR,
                "labels": labels,
                "badge": None,
                "repo_name": short,
                "branch_arrow": {
                    "head": pr.head.ref if pr.head else "",
                    "base": pr.base.ref if pr.base else "",
                },
                "commit_sha": None,
                "extra_subline": None,
                "time_display": time_display(merged_utc),
                "bullets": body_bullets(pr.body),
                "show_meta_row": True,
                "diffstat": {
                    "add": pr.additions,
                    "del": pr.deletions,
                    "files": pr.changed_files,
                },
                "linear": extract_linear(f"{pr.title}\n{pr.head.ref if pr.head else ''}\n{pr.body or ''}"),
                "author": {
                    "handle": author.login if author else "ghost",
                    "initial": initial(author.login if author else "?"),
                    "profile_url": author.html_url if author else "#",
                    "avatar_url": author.avatar_url if author else "",
                    "color_idx": color_idx_for(author.login if author else "ghost"),
                },
            }
            items.append(FetchedItem("merged", merged_utc.timestamp(), payload))
    except GithubException as e:
        print(f"    ! closed PR 가져오기 실패: {e.data.get('message', e)}", file=sys.stderr)

    # ---- 열려 있는 PR (open + draft) ----
    try:
        opens = repo.get_pulls(state="open", sort="updated", direction="desc")
        for pr in opens[:30]:
            gh_labels = [lbl.name for lbl in pr.labels]
            labels = infer_labels(pr.title, pr.head.ref if pr.head else "", gh_labels, keyword_map)
            author = pr.user
            is_draft = pr.draft
            badge = {"cls": "draft", "text": "Draft"} if is_draft else {"cls": "review", "text": "Review 대기"}
            created_utc = pr.created_at.replace(tzinfo=timezone.utc) if pr.created_at.tzinfo is None else pr.created_at
            updated_utc = pr.updated_at.replace(tzinfo=timezone.utc) if pr.updated_at.tzinfo is None else pr.updated_at
            payload = {
                "url": pr.html_url,
                "title": pr.title,
                "id_display": f"#{pr.number}",
                "status_class": "draft" if is_draft else "open",
                "status_svg": ICON_DRAFT_PR if is_draft else ICON_OPEN_PR,
                "labels": labels,
                "badge": badge,
                "repo_name": short,
                "branch_arrow": {
                    "head": pr.head.ref if pr.head else "",
                    "base": pr.base.ref if pr.base else "",
                },
                "commit_sha": None,
                "extra_subline": None,
                "time_display": time_display(created_utc),
                "bullets": body_bullets(pr.body),
                "show_meta_row": True,
                "diffstat": {
                    "add": pr.additions,
                    "del": pr.deletions,
                    "files": pr.changed_files,
                },
                "linear": extract_linear(f"{pr.title}\n{pr.head.ref if pr.head else ''}\n{pr.body or ''}"),
                "author": {
                    "handle": author.login if author else "ghost",
                    "initial": initial(author.login if author else "?"),
                    "profile_url": author.html_url if author else "#",
                    "avatar_url": author.avatar_url if author else "",
                    "color_idx": color_idx_for(author.login if author else "ghost"),
                },
            }
            items.append(FetchedItem("open", updated_utc.timestamp(), payload))
    except GithubException as e:
        print(f"    ! open PR 가져오기 실패: {e.data.get('message', e)}", file=sys.stderr)

    # ---- 오늘 성공한 deploy/release workflow run ----
    deploy_keywords = [k.lower() for k in cfg.get("deploy_workflow_keywords", [])]
    if deploy_keywords:
        try:
            runs = repo.get_workflow_runs(status="success")
            count = 0
            for run in runs[:50]:
                created_utc = run.created_at.replace(tzinfo=timezone.utc) if run.created_at.tzinfo is None else run.created_at
                if created_utc < today_start_utc:
                    break
                if created_utc > today_end_utc:
                    continue
                wf_name = (run.name or "").lower()
                if not any(kw in wf_name for kw in deploy_keywords):
                    continue
                actor = run.actor
                short_sha = (run.head_sha or "")[:7]
                # 환경 판정 (heuristic)
                if "staging" in wf_name or "stage" in wf_name:
                    env_badge = {"cls": "staging", "text": "staging"}
                else:
                    env_badge = {"cls": "prod", "text": "prod"}
                payload = {
                    "url": run.html_url,
                    "title": run.display_title or run.name or "Deploy",
                    "id_display": None,
                    "status_class": "deploy",
                    "status_svg": ICON_DEPLOY,
                    "labels": ["release"],
                    "badge": env_badge,
                    "repo_name": short,
                    "branch_arrow": None,
                    "commit_sha": short_sha,
                    "extra_subline": run.name,
                    "time_display": time_display(created_utc),
                    "bullets": [],
                    "show_meta_row": False,
                    "diffstat": None,
                    "linear": None,
                    "author": {
                        "handle": actor.login if actor else "ghost",
                        "initial": initial(actor.login if actor else "?"),
                        "profile_url": actor.html_url if actor else "#",
                        "avatar_url": actor.avatar_url if actor else "",
                        "color_idx": color_idx_for(actor.login if actor else "ghost"),
                    },
                }
                items.append(FetchedItem("deployed", created_utc.timestamp(), payload))
                count += 1
                if count >= 5:
                    break  # repo 하나당 너무 많은 deploy는 컷
        except GithubException as e:
            print(f"    ! workflow run 가져오기 실패: {e.data.get('message', e)}", file=sys.stderr)

    return items


# ---------------------------------------------------------------------------
# Render
# ---------------------------------------------------------------------------

def render(cfg: dict, fetched: list[FetchedItem], built_at: datetime) -> str:
    deployed = [i.payload for i in sorted([x for x in fetched if x.section == "deployed"], key=lambda x: -x.sort_key)]
    merged = [i.payload for i in sorted([x for x in fetched if x.section == "merged"], key=lambda x: -x.sort_key)]
    opens = [i.payload for i in sorted([x for x in fetched if x.section == "open"], key=lambda x: -x.sort_key)]

    open_visible_n = int(cfg.get("open_visible", 4))
    open_visible = opens[:open_visible_n]
    open_hidden = opens[open_visible_n:]

    repos_short = [short_repo(r) for r in cfg["repos"]]

    sections_cfg = cfg.get("sections", {})

    today_local = datetime.now(KST)
    weekday_ko = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"][today_local.weekday()]
    ctx = {
        "title": cfg.get("display", {}).get("title", "오늘의 작업"),
        "date_iso": today_local.strftime("%Y-%m-%d"),
        "date_display": f"{today_local.strftime('%Y-%m-%d')} ({weekday_ko})",
        "refresh_display": "방금 갱신됨",
        "repos": repos_short,
        "sections": {
            "deployed": sections_cfg.get("deployed", True),
            "merged": sections_cfg.get("merged", True),
            "open": sections_cfg.get("open", True),
        },
        "deployed": deployed,
        "merged": merged,
        "open_visible": open_visible,
        "open_hidden": open_hidden,
        "open_total": len(opens),
        "cron_display": "09:00 KST",
        "built_at_display": built_at.astimezone(KST).strftime("%Y-%m-%d %H:%M KST"),
    }

    env = Environment(
        loader=FileSystemLoader(str(ROOT)),
        autoescape=select_autoescape(["html"]),
        trim_blocks=False,
        lstrip_blocks=False,
    )
    tmpl = env.get_template("template.html")
    return tmpl.render(ctx=ctx)


def write_summary(cfg: dict, fetched: list[FetchedItem]) -> dict:
    summary = {
        "date": datetime.now(KST).strftime("%Y-%m-%d"),
        "weekday": ["월", "화", "수", "목", "금", "토", "일"][datetime.now(KST).weekday()],
        "counts": {
            "deployed": sum(1 for x in fetched if x.section == "deployed"),
            "merged": sum(1 for x in fetched if x.section == "merged"),
            "open": sum(1 for x in fetched if x.section == "open"),
        },
        "highlights": {
            "merged": [
                {"title": x.payload["title"], "url": x.payload["url"], "repo": x.payload["repo_name"], "author": x.payload["author"]["handle"]}
                for x in sorted([i for i in fetched if i.section == "merged"], key=lambda x: -x.sort_key)[:3]
            ],
            "deployed": [
                {"title": x.payload["title"], "url": x.payload["url"], "repo": x.payload["repo_name"]}
                for x in sorted([i for i in fetched if i.section == "deployed"], key=lambda x: -x.sort_key)[:3]
            ],
        },
        "dashboard_url": cfg.get("display", {}).get("public_url", ""),
    }
    SUMMARY_PATH.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    return summary


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def resolve_github_token() -> str | None:
    """GITHUB_TOKEN 환경 변수 → 없으면 `gh auth token` fallback."""
    tok = os.environ.get("GITHUB_TOKEN", "").strip()
    if tok:
        return tok
    gh = shutil.which("gh")
    if not gh:
        return None
    try:
        result = subprocess.run(
            [gh, "auth", "token"],
            check=True,
            capture_output=True,
            text=True,
            timeout=5,
        )
        return result.stdout.strip() or None
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
        return None


def main() -> int:
    token = resolve_github_token()
    if not token:
        print(
            "ERROR: GitHub 인증을 찾지 못했습니다.\n"
            "  옵션 1) 환경 변수 GITHUB_TOKEN 설정\n"
            "  옵션 2) `gh auth login` 으로 GitHub CLI 인증",
            file=sys.stderr,
        )
        return 1

    cfg = yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8"))
    repos: list[str] = cfg["repos"]
    if not repos:
        print("ERROR: config.yml의 repos 목록이 비어 있습니다.", file=sys.stderr)
        return 1

    # 오늘의 KST 자정 ~ 다음 자정을 UTC 범위로 변환
    now_kst = datetime.now(KST)
    start_kst = now_kst.replace(hour=0, minute=0, second=0, microsecond=0)
    end_kst = start_kst + timedelta(days=1)
    today_start_utc = start_kst.astimezone(timezone.utc)
    today_end_utc = end_kst.astimezone(timezone.utc)

    print(f"수집 범위: {today_start_utc.isoformat()} ~ {today_end_utc.isoformat()}")
    print(f"대상 repo: {len(repos)}개")

    auth = Auth.Token(token)
    gh = Github(auth=auth, per_page=100)

    all_items: list[FetchedItem] = []
    for full in repos:
        try:
            all_items.extend(fetch_repo(gh, full, cfg, today_start_utc, today_end_utc))
        except GithubException as e:
            print(f"  ! {full} 전체 조회 실패: {e.data.get('message', e)}", file=sys.stderr)

    built_at = datetime.now(timezone.utc)
    html = render(cfg, all_items, built_at)

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(html, encoding="utf-8")
    summary = write_summary(cfg, all_items)

    print()
    print(f"빌드 완료 → {OUTPUT_PATH.relative_to(ROOT)}")
    print(f"  배포됨: {summary['counts']['deployed']}건")
    print(f"  머지됨: {summary['counts']['merged']}건")
    print(f"  진행 중: {summary['counts']['open']}건")
    return 0


if __name__ == "__main__":
    sys.exit(main())
