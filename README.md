# Daily Work Dashboard

매일 09:00 KST, Tesser repo들의 당일 활동(머지된 PR, 진행 중 PR, 배포)을 수집해 HTML 대시보드로 빌드하고 GitHub Pages에 배포 + Slack 알림.

## 구조

```
build.py          — GitHub API 조회 → docs/index.html 렌더링
publish.sh        — git commit & push (Pages 배포)
config.yml        — 추적 repo 목록, 라벨 규칙
template.html     — Jinja2 템플릿
daily_prompt.md   — scheduled task prompt
```

## 사용법

```bash
pip install -r requirements.txt
python3 build.py        # 빌드
bash publish.sh         # 배포
```

디자인만 확인: `python3 dev_render_sample.py && open docs/index.html`

## 설정

- 추적 repo 변경: `config.yml` → `repos`
- 라벨 규칙: `config.yml` → `label_keywords`
- Pages: Settings → Pages → main branch / /docs folder
