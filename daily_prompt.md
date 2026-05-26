# Cowork scheduled task용 프롬프트

매일 9시에 Cowork이 이 prompt를 실행하도록 등록합니다.

현재 설정:
- 호스팅 repo: `jeongwoo0122/daily-work-dashboard`
- Pages URL: `https://jeongwoo0122.github.io/daily-work-dashboard/`
- Slack 대상: `D072AV3B7V2` (개인 DM)
- 빌드 폴더: 사용자가 git clone한 위치 (아래 prompt의 `WORKDIR` 변수 채우기)

---

## 등록용 prompt (그대로 복사해서 사용)

```
오늘의 작업 대시보드 자동 갱신. 사용자에게 묻지 말고 아래 순서대로 실행:

WORKDIR=<여기에 git clone한 절대경로 입력 예: /Users/jeongwoo/projects/daily-work-dashboard>

1. cd $WORKDIR && python3 build.py
   - 실패하면 5번으로 가서 실패 메시지만 Slack에 보고 후 종료.

2. cd $WORKDIR && bash publish.sh
   - "변경사항 없음" 이면 정상. 다음 단계 진행.

3. $WORKDIR/build_summary.json 읽기.

4. Slack 채널 D072AV3B7V2 (개인 DM)에 slack_send_message로 메시지 전송.
   message 본문은 다음 markdown 포맷:

   ☀️ **오늘의 작업 — {date} ({weekday})**

   **배포** `{deployed}` · **머지** `{merged}` · **진행 중** `{open}`

   **오늘 머지된 PR** (highlights.merged 가 비어있으면 이 블록 생략)
   • [{title}]({url}) _({repo} · @{author})_  ← 항목당 한 줄, 최대 3건

   **오늘 배포** (highlights.deployed 가 비어있으면 이 블록 생략)
   • [{title}]({url}) _({repo})_

   [전체 대시보드 보기 →](https://jeongwoo0122.github.io/daily-work-dashboard/)

5. 모든 단계 성공이면 한 줄로 결과만 응답: "완료 — 머지 N건 / 배포 N건 / 진행 중 N건"
   실패 시: 실패 단계와 원인을 한국어로 한 줄 응답 + Slack에 :warning: 메시지 전송.

특이사항: 절대 사용자에게 확인 질문을 하지 말 것 (자동 실행이므로). 의문이 들면 가장 보수적인 기본값으로 진행하고 응답에 적기.
```

---

## 등록 방법

Claude에게 다음과 같이 말하면 자동 등록됨:

> 위 prompt의 WORKDIR을 `/내/실제/경로`로 채우고, 매일 오전 9시에 실행되는 scheduled task로 등록해줘.

또는 직접 `mcp__scheduled-tasks__create_scheduled_task` 호출:
- prompt: 위 prompt 블록 (WORKDIR 채워서)
- cronExpression: `"0 9 * * *"` (사용자 local time 기준)
