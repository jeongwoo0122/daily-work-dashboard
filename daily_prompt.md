# Cowork scheduled task용 프롬프트

매일 9시 KST에 Cowork이 이 prompt를 실행하도록 등록합니다.
`{{SLACK_CHANNEL}}` 부분만 실제 채널명 (예: `#dev-daily`)으로 치환하세요.

---

## 등록용 prompt (이걸 그대로 복사해서 사용)

```
오늘의 작업 대시보드 자동 갱신. 사용자에게 묻지 말고 아래 순서대로 실행:

1. cd /Users/ham/.config/cowork-secrets/daily-work-dashboard && python3 build.py
   - 실패하면 5번으로 가서 실패 메시지만 Slack에 보고 후 종료.

2. cd /Users/ham/.config/cowork-secrets/daily-work-dashboard && bash publish.sh
   - "변경사항 없음" 이면 정상. 다음 단계 진행.

3. /Users/ham/.config/cowork-secrets/daily-work-dashboard/build_summary.json 읽기.

4. Slack의 {{SLACK_CHANNEL}} 채널에 slack_send_message로 메시지 전송:
   - text: "오늘의 작업 — {date} ({weekday}) · 배포 {deployed} / 머지 {merged} / 진행 중 {open}"
   - blocks:
     a) header: ":sunny: 오늘의 작업 — {date} ({weekday})"
     b) section (mrkdwn): "*배포* `{deployed}` · *머지* `{merged}` · *진행 중* `{open}`"
     c) highlights.merged 가 비어있지 않으면 section (mrkdwn):
        "*오늘 머지된 PR*\n" + 항목당 한 줄: "• <{url}|{title}> _({repo} · @{author})_"
     d) highlights.deployed 가 비어있지 않으면 section (mrkdwn):
        "*오늘 배포*\n" + 항목당 한 줄: "• <{url}|{title}> _({repo})_"
     e) actions: button "전체 대시보드 보기 →" → https://tesser.github.io/daily-work-dashboard/  (style: primary)
     f) divider

5. 모든 단계 성공이면 짧게 한 줄로 결과만 응답: "완료 — 머지 N건 / 배포 N건 / 진행 중 N건"
   실패 시: 실패 단계와 원인을 한국어로 한 줄 응답 + 가능하면 Slack에 :warning: 메시지 전송.

특이사항: 절대 사용자에게 확인 질문을 하지 말 것 (자동 실행이므로). 의문이 들면 가장 보수적인 기본값으로 진행하고 응답에 적기.
```

---

## 등록 방법

Claude에게 다음과 같이 말하면 자동 등록됨:

> 위 prompt를 매일 오전 9시 (KST)에 실행되는 scheduled task로 등록해줘.
> 채널은 `#dev-daily` (또는 결정한 채널)로.

또는 직접 `mcp__scheduled-tasks__create_scheduled_task` 호출:
- name: "오늘의 작업 대시보드 갱신"
- prompt: 위 prompt 블록
- cronExpression: "0 9 * * *" (사용자 local time 기준)
