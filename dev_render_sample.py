#!/usr/bin/env python3
"""
샘플 데이터로 template.html을 렌더링해서 docs/index.html에 출력합니다.
GitHub API 없이도 디자인을 즉시 확인하기 위한 로컬 전용 스크립트.

사용:
  python3 dev_render_sample.py
  open docs/index.html
"""
from __future__ import annotations

import sys
from pathlib import Path

import yaml

# build.py에서 렌더링 로직과 아이콘 재사용
sys.path.insert(0, str(Path(__file__).resolve().parent))
from build import (
    ICON_DEPLOY,
    ICON_DRAFT_PR,
    ICON_MERGED_PR,
    ICON_OPEN_PR,
    FetchedItem,
    OUTPUT_PATH,
    ROOT,
    color_idx_for,
    initial,
    render,
)
from datetime import datetime, timezone


def make_pr(section, sort_key, **kwargs):
    """기본값을 채워 넣는 헬퍼."""
    base = {
        "url": "#",
        "title": "",
        "id_display": None,
        "status_class": "open",
        "status_svg": ICON_OPEN_PR,
        "labels": [],
        "badge": None,
        "repo_name": "ontol-clinics-backend",
        "branch_arrow": None,
        "commit_sha": None,
        "extra_subline": None,
        "time_display": "10:00 KST",
        "bullets": [],
        "show_meta_row": True,
        "diffstat": None,
        "linear": None,
        "author": {
            "handle": "demo",
            "initial": "D",
            "profile_url": "#",
            "avatar_url": "",
            "color_idx": 0,
        },
    }
    base.update(kwargs)
    return FetchedItem(section, sort_key, base)


def main() -> int:
    cfg = yaml.safe_load((ROOT / "config.yml").read_text(encoding="utf-8"))

    items: list[FetchedItem] = [
        # 배포됨
        make_pr(
            "deployed", 1000,
            url="https://github.com/Tesser/ontol-clinics-backend/actions/runs/9123456",
            title="Release v1.42.0 — billing fixes",
            labels=["release"],
            badge={"cls": "prod", "text": "prod"},
            status_class="deploy",
            status_svg=ICON_DEPLOY,
            repo_name="ontol-clinics-backend",
            commit_sha="a3f2c1d",
            extra_subline="2 PRs 포함",
            time_display="12:34 KST",
            author={"handle": "hyungtae", "initial": "H", "profile_url": "https://github.com/hyungtae", "avatar_url": "", "color_idx": color_idx_for("hyungtae")},
        ),
        make_pr(
            "deployed", 900,
            url="https://github.com/Tesser/ontol-for-clinics-admin/actions/runs/9123488",
            title="Deploy admin — onboarding events",
            labels=["release"],
            badge={"cls": "staging", "text": "staging"},
            status_class="deploy",
            status_svg=ICON_DEPLOY,
            repo_name="ontol-for-clinics-admin",
            commit_sha="b71e9a8",
            extra_subline="2 PRs 포함",
            time_display="15:02 KST",
            author={"handle": "minji", "initial": "M", "profile_url": "https://github.com/minji", "avatar_url": "", "color_idx": color_idx_for("minji")},
        ),
        # 머지됨
        make_pr(
            "merged", 800,
            url="https://github.com/Tesser/ontol-clinics-backend/pull/1234",
            title="Add user search endpoint",
            id_display="#1234",
            labels=["feat"],
            status_class="merged",
            status_svg=ICON_MERGED_PR,
            repo_name="ontol-clinics-backend",
            branch_arrow={"head": "feat/user-search", "base": "main"},
            time_display="11:08 KST",
            bullets=[
                "이름·이메일로 검색하는 API 엔드포인트 추가",
                "페이지네이션 (페이지당 20건) 지원",
                "관리자 페이지에서 사용 예정",
            ],
            diffstat={"add": 180, "del": 20, "files": 7},
            linear={"id": "ENG-412", "url": "https://linear.app/tesser/issue/ENG-412"},
            author={"handle": "hyungtae", "initial": "H", "profile_url": "https://github.com/hyungtae", "avatar_url": "", "color_idx": color_idx_for("hyungtae")},
        ),
        make_pr(
            "merged", 780,
            url="https://github.com/Tesser/ontol-clinics-backend/pull/1231",
            title="Fix N+1 in billing query",
            id_display="#1231",
            labels=["fix", "perf"],
            status_class="merged",
            status_svg=ICON_MERGED_PR,
            repo_name="ontol-clinics-backend",
            branch_arrow={"head": "fix/billing-n-plus-1", "base": "main"},
            time_display="11:54 KST",
            bullets=["청구 조회 API에서 N+1 쿼리 발견", "join으로 묶어 단일 쿼리로 해결"],
            diffstat={"add": 45, "del": 62, "files": 3},
            linear=None,
            author={"handle": "minji", "initial": "M", "profile_url": "https://github.com/minji", "avatar_url": "", "color_idx": color_idx_for("minji")},
        ),
        make_pr(
            "merged", 760,
            url="https://github.com/Tesser/ontol-for-clinics-gui-application/pull/812",
            title="Onboarding step 3 analytics",
            id_display="#812",
            labels=["feat"],
            status_class="merged",
            status_svg=ICON_MERGED_PR,
            repo_name="ontol-for-clinics-gui-application",
            branch_arrow={"head": "feat/onboarding-events", "base": "main"},
            time_display="13:21 KST",
            bullets=["온보딩 3단계에 분석 이벤트 추가", "이탈 지점 추적 가능"],
            diffstat={"add": 120, "del": 5, "files": 6},
            author={"handle": "jiwon", "initial": "J", "profile_url": "https://github.com/jiwon", "avatar_url": "", "color_idx": color_idx_for("jiwon")},
        ),
        # 진행 중
        make_pr(
            "open", 700,
            url="https://github.com/Tesser/ontol-clinics-backend/pull/1240",
            title="Stripe webhook retry policy",
            id_display="#1240",
            labels=["feat"],
            status_class="draft",
            status_svg=ICON_DRAFT_PR,
            badge={"cls": "draft", "text": "Draft"},
            repo_name="ontol-clinics-backend",
            branch_arrow={"head": "feat/stripe-retry", "base": "main"},
            time_display="09:12에 열림",
            bullets=["Stripe 웹훅 실패 시 재시도 정책 도입", "지수적 백오프 적용 예정"],
            diffstat={"add": 95, "del": 5, "files": 4},
            author={"handle": "hyungtae", "initial": "H", "profile_url": "https://github.com/hyungtae", "avatar_url": "", "color_idx": color_idx_for("hyungtae")},
        ),
        make_pr(
            "open", 680,
            url="https://github.com/Tesser/ontol-clinics-backend/pull/1239",
            title="Add audit log table migration",
            id_display="#1239",
            labels=["feat"],
            badge={"cls": "review", "text": "Review 대기"},
            repo_name="ontol-clinics-backend",
            branch_arrow={"head": "feat/audit-log", "base": "main"},
            time_display="10:01에 열림",
            bullets=["감사 로그용 신규 테이블 마이그레이션", "컬럼 스키마와 인덱스 의견 필요"],
            diffstat={"add": 210, "del": 0, "files": 5},
            linear={"id": "ENG-418", "url": "https://linear.app/tesser/issue/ENG-418"},
            author={"handle": "minji", "initial": "M", "profile_url": "https://github.com/minji", "avatar_url": "", "color_idx": color_idx_for("minji")},
        ),
        make_pr(
            "open", 660,
            url="https://github.com/Tesser/ontol-for-clinics-client/pull/815",
            title="Settings — Notifications redesign",
            id_display="#815",
            labels=["design"],
            status_class="draft",
            status_svg=ICON_DRAFT_PR,
            badge={"cls": "draft", "text": "Draft"},
            repo_name="ontol-for-clinics-client",
            branch_arrow={"head": "design/notif-redesign", "base": "main"},
            time_display="10:48에 열림",
            bullets=["설정 화면 알림 섹션 재디자인", "디자인 시안 검토 중"],
            diffstat={"add": 180, "del": 60, "files": 9},
            author={"handle": "sumin", "initial": "S", "profile_url": "https://github.com/sumin", "avatar_url": "", "color_idx": color_idx_for("sumin")},
        ),
        make_pr(
            "open", 640,
            url="https://github.com/Tesser/ontol-for-clinics-user-story/pull/22",
            title="Remove dead /legacy routes",
            id_display="#22",
            labels=["chore"],
            badge={"cls": "review", "text": "Review 대기"},
            repo_name="ontol-for-clinics-user-story",
            branch_arrow={"head": "chore/remove-legacy", "base": "main"},
            time_display="11:22에 열림",
            bullets=["미사용 /legacy 경로 정리", "관련 컴포넌트 일괄 제거"],
            diffstat={"add": 0, "del": 340, "files": 18},
            author={"handle": "jiwon", "initial": "J", "profile_url": "https://github.com/jiwon", "avatar_url": "", "color_idx": color_idx_for("jiwon")},
        ),
        # 진행 중 — 접힘 영역에 들어갈 추가 항목들
        make_pr(
            "open", 620,
            url="https://github.com/Tesser/ontol-clinics-backend/pull/1238",
            title="Rate limit for /v1/search",
            id_display="#1238",
            labels=["feat", "security"],
            badge={"cls": "review", "text": "Review 대기"},
            repo_name="ontol-clinics-backend",
            branch_arrow={"head": "feat/search-ratelimit", "base": "main"},
            time_display="어제 열림",
            bullets=["검색 API에 rate limit 도입", "IP·토큰 단위 적용"],
            diffstat={"add": 150, "del": 10, "files": 6},
            author={"handle": "hyungtae", "initial": "H", "profile_url": "https://github.com/hyungtae", "avatar_url": "", "color_idx": color_idx_for("hyungtae")},
        ),
        make_pr(
            "open", 600,
            url="https://github.com/Tesser/ontol-clinic-be-server-smc/pull/12",
            title="Background job for report export",
            id_display="#12",
            labels=["feat"],
            status_class="draft",
            status_svg=ICON_DRAFT_PR,
            badge={"cls": "draft", "text": "Draft"},
            repo_name="ontol-clinic-be-server-smc",
            branch_arrow={"head": "feat/bg-report-export", "base": "main"},
            time_display="2일 전 열림",
            bullets=["리포트 내보내기를 백그라운드 잡으로 분리", "대용량 처리 안정성 확보"],
            diffstat={"add": 320, "del": 40, "files": 11},
            author={"handle": "minji", "initial": "M", "profile_url": "https://github.com/minji", "avatar_url": "", "color_idx": color_idx_for("minji")},
        ),
    ]

    html = render(cfg, items, datetime.now(timezone.utc))
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(html, encoding="utf-8")
    print(f"샘플 렌더링 완료 → {OUTPUT_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
