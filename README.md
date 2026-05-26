# 오늘의 작업 대시보드

매일 아침 09:00 KST, Cowork이 자동으로:
1. 6개 Tesser repo의 오늘 활동을 GitHub API로 조회
2. HTML 대시보드를 빌드
3. `Tesser/daily-work-dashboard` repo에 push → GitHub Pages 자동 배포
4. Slack 채널에 짧은 요약 + Pages URL 전송

추적 대상은 `config.yml`에서 변경할 수 있습니다.

---

## 흐름

```
[매일 9시 Cowork scheduled task 발동]
        ↓
python3 build.py
   · GitHub MCP 또는 gh CLI 토큰으로 6개 repo 조회
   · 오늘 머지된 PR, 진행 중 PR, 성공한 deploy/release run 수집
   · template.html에 렌더 → docs/index.html 생성
   · build_summary.json (Slack용 데이터) 생성
        ↓
bash publish.sh
   · git add docs/index.html → commit → push
   · GitHub Pages가 자동으로 새 페이지 배포 (1~2분)
        ↓
Claude가 build_summary.json을 읽어
Slack MCP로 #채널에 요약 메시지 전송
   · 배포/머지/진행 중 카운트
   · 머지된 PR 상위 3건 링크
   · "전체 대시보드 보기 →" 버튼 (Pages URL)
```

GitHub Actions, PAT 발급, webhook 발급, secrets 등록은 사용하지 않습니다.

---

## 셋업 (한 번만)

### 1. GitHub Pages 호스팅용 repo 생성

GitHub에서 `Tesser/daily-work-dashboard` repo를 새로 만듭니다. private/public 무엇이든 OK (단, 무료 플랜의 private repo는 Pages가 제한될 수 있음).

### 2. 이 폴더를 그 repo로 초기화

```bash
cd ~/.config/cowork-secrets/daily-work-dashboard
git init -b main
git add .
git commit -m "Initial: daily work dashboard"
git remote add origin git@github.com:Tesser/daily-work-dashboard.git
git push -u origin main
```

### 3. GitHub Pages 활성화

저장소 → **Settings → Pages**:
- Source: **Deploy from a branch**
- Branch: **main** / **/docs**

저장하면 1~2분 후 `https://tesser.github.io/daily-work-dashboard/` URL이 발급됩니다.

### 4. gh CLI 인증 확인

```bash
gh auth status
```

미인증이면:
```bash
gh auth login   # GitHub.com → HTTPS → Login with browser
```

build.py는 `GITHUB_TOKEN` 환경 변수가 없으면 자동으로 `gh auth token`을 호출해 토큰을 가져옵니다. 6개 Tesser repo에 대한 읽기 권한이 gh 인증 계정에 있어야 합니다.

### 5. Slack 채널 결정 + Cowork에 Slack 연결 확인

게시할 채널 (예: `#dev-daily`) 정하기. Cowork에 Slack MCP가 이미 연결되어 있으면 추가 작업 없음.

### 6. Scheduled task 등록

Cowork에게 다음과 같이 말하세요:

> `daily_prompt.md` 안의 prompt를 매일 오전 9시 (KST)에 실행되는 scheduled task로 등록해줘. 채널은 #dev-daily.

또는 직접 등록하려면 `daily_prompt.md`의 prompt를 복사해 `mcp__scheduled-tasks__create_scheduled_task` 호출:
- **prompt**: `daily_prompt.md`의 prompt 블록 (채널명 치환)
- **cronExpression**: `"0 9 * * *"` (사용자 local time 기준)

### 7. 첫 실행 테스트

scheduled task 등록 후, Cowork에게 "지금 한 번 돌려봐"라고 시켜서 한 번 실행시켜보고 Slack에 메시지가 잘 도착하는지 확인하세요.

---

## 로컬 수동 빌드

scheduled task 없이 그냥 한 번 돌리려면:

```bash
cd ~/.config/cowork-secrets/daily-work-dashboard
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python3 build.py
open docs/index.html         # macOS — 브라우저로 결과 확인
bash publish.sh              # GitHub Pages로 push
```

---

## 샘플로 디자인만 확인

GitHub API 호출 없이 mock 데이터로 디자인만 빠르게 보고 싶다면:

```bash
python3 dev_render_sample.py
open docs/index.html
```

---

## 자주 하는 변경

### 추적할 repo 추가/제거
`config.yml`의 `repos` 목록 편집. gh CLI 계정에 해당 repo 읽기 권한만 있으면 됨.

### 실행 시간 변경
scheduled task의 cron 수정 — Cowork에게 "스케줄을 매일 18시로 바꿔줘" 라고 말하면 됨.

### Slack 메시지 포맷 변경
`daily_prompt.md`의 prompt 텍스트를 수정하고 scheduled task를 업데이트.

### 라벨 (feat/fix/perf...) 추론 규칙
`config.yml`의 `label_keywords`에서 키워드 추가/제거.

### Deploy로 인식하는 워크플로우 키워드
`config.yml`의 `deploy_workflow_keywords` 수정.

---

## 트러블슈팅

**Cowork이 매일 9시에 안 깨움**
- Cowork은 Claude 데스크톱 앱이 켜져 있는 동안만 scheduled task를 실행합니다. 휴가/주말에 노트북을 닫아두면 그 시간엔 실행되지 않습니다.
- 24/7 보장이 필요하면 `archive/` 폴더의 GitHub Actions 버전을 참고하거나, EC2 같은 항상 켜진 머신으로 옮기세요.

**build.py가 "GitHub 인증을 찾지 못했습니다"**
- `gh auth status`로 확인. 미인증이면 `gh auth login`. 인증되어 있는데도 실패하면 `gh auth token`이 실제로 토큰을 출력하는지 직접 확인.

**publish.sh가 "git repo가 아닙니다"**
- 셋업 2번 단계를 건너뛰었습니다. `git init` + `git remote add origin ...` + 첫 push.

**Pages URL이 404**
- Settings → Pages에서 Source가 `main` 브랜치 + `/docs` 폴더로 설정됐는지 확인. 첫 push 후 1~2분 기다리세요.

**페이지가 비어 있음**
- 정상 — 오늘 활동이 없으면 각 섹션이 "없습니다"로 표시됩니다.

**시간대가 안 맞음**
- scheduled task의 cron은 사용자 mac의 local timezone 기준입니다.

---

## 구조

```
daily-work-dashboard/
├── build.py                ← GitHub API → HTML 렌더링
├── publish.sh              ← git commit & push
├── template.html           ← 디자인 (Jinja2)
├── config.yml              ← repo 목록, 라벨 규칙, 표시 옵션
├── daily_prompt.md         ← scheduled task에 등록할 prompt 본문
├── dev_render_sample.py    ← mock 데이터로 디자인 미리보기
├── requirements.txt
├── docs/                   ← GitHub Pages 소스
│   └── index.html          ← build.py가 매일 새로 만드는 파일
└── README.md
```

build.py 출력물:
- `docs/index.html` — Pages에 push될 결과물
- `build_summary.json` — Slack 메시지 작성용 카운트/하이라이트
