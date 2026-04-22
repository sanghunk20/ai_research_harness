현재 연구 로드맵상의 진행 위치를 파악하고, 그 위치부터 `harness/execute.py`를 호출하여 연구를 이어가라.

**이 커맨드는 execute.py의 얇은 래퍼다.** 실제 step 실행, retry, tmux, polling, git commit은 execute.py가 담당한다. `/harness`의 책임은:
1. 로드맵 스캔 → 다음 실행할 phase 선정
2. 연구자에게 현재 위치 보고 및 진행 방식 확인
3. execute.py 호출 (`python harness/execute.py <phase-dir>` 혹은 `--resume`)
4. 완료 후 PROJ-001 동기화

## 실행 절차

### 1. 사전 조건 확인

- `projects/phases/index.json`이 존재하고 `phases` 배열이 비어있지 않은지 확인
- `projects/PROJ-*.md`가 존재하는지 확인
- `harness/execute.py`의 `CONDA_ENV`/`TRAIN_USER` placeholder(`{CONDA_ENV}`, `{TRAIN_USER}`)가 실값으로 치환되어 있는지 확인

하나라도 실패하면: "`/setup`을 먼저 실행해 주세요." 로 중단.

### 2. 현재 진행 위치 파악

`projects/phases/index.json`을 읽고 다음 규칙으로 **다음 실행할 phase**를 결정:

1. **우선순위 1**: `status == "training"` — 이미 학습 중인 phase. `--resume`으로 재개 대상.
2. **우선순위 2**: `status == "in_progress"` — 진행 중인 phase.
3. **우선순위 3**: `status == "pending"` 중 배열상 가장 앞쪽 phase.
4. **blocked / error phase**: 별도 목록으로 수집하여 보고. 현재 phase 선정에서는 제외.
5. 모든 phase가 `completed`: "모든 phase 완료" 보고 후 중단.

선정된 phase의 `projects/phases/<dir>/index.json`도 같이 읽어서 다음 step 정보를 파악한다 (execute.py가 자동으로 진행하지만, 보고용으로 필요).

### 3. 진행 상황 요약 보고

다음 형식으로 출력:

```
## 연구 진행 현황

**프로젝트**: <project>
**다음 실행 대상**: <dir> — '<name>'
**다음 step**: step <N> ('<step-name>') — type: <type>
**재개 모드**: <해당되는 경우, training 상태라 --resume 사용>

**로드맵 전체 진행률**:
  [done] phase-baseline            (completed)
  [ .. ] phase-proposal             (training — step 2, tmux: harness-phase-proposal-2)
  [    ] phase-ablation             (pending)
  [WAIT] phase-analysis             (blocked — <blocked_reason 한 줄>)
  [FAIL] phase-extension            (error — <error_message 한 줄>)

**전체 통계**: completed <X> / in_progress <Y> / training <Z> / pending <W> / blocked <B> / error <E>
```

이미 `training` 상태인 step이 있으면 tmux 세션 상태도 같이 보여준다:
```bash
tmux has-session -t <tmux_session> 2>/dev/null && echo "session alive" || echo "session ended"
```

### 4. 진행 방식 선택 (AskUserQuestion)

선정된 phase가 **`training` 상태**이면:
1. "학습 완료 후 재개(`--resume`)" — execute.py를 `--resume` 플래그와 호출
2. "상태만 확인(`--status`)" — `python harness/execute.py <dir> --status`
3. "취소"

그 외의 경우:
1. **선정된 phase 실행** — `python harness/execute.py <dir>`
2. **실행 계획만 확인(`--dry-run`)** — 실제 실행 없이 계획 출력
3. **다른 phase 선택** — AskUserQuestion으로 phase dir 목록 제시
4. **blocked/error phase 해결** — blocked·error 목록이 있을 때만
5. **취소**

### 5. execute.py 호출

선택에 따라 실행:

```bash
# 일반 실행
python harness/execute.py <dir>

# 학습 완료 후 재개
python harness/execute.py <dir> --resume

# 실행 계획 확인
python harness/execute.py <dir> --dry-run

# 상태만 확인
python harness/execute.py <dir> --status

# 특정 step만
python harness/execute.py <dir> --step <N>
```

execute.py가 Claude CLI를 subprocess로 호출하여 각 step을 수행하고, retry 3회, tmux 관리, 학습 polling까지 자동 처리한다. `/harness`는 execute.py의 출력(stdout/stderr)을 연구자에게 그대로 전달한다.

**주의**:
- execute.py가 `feat-<phase-name>` 브랜치로 자동 체크아웃한다. 현재 브랜치에 커밋하지 않은 변경이 있으면 execute.py가 실패하니 먼저 커밋/stash를 권한다.
- execute.py가 각 step 완료 시 자동 git commit을 생성한다. 별도의 커밋이 필요 없다.

### 6. 실행 결과 후처리

execute.py가 종료된 뒤:

1. `projects/phases/index.json`과 해당 phase의 `index.json`의 최신 상태를 읽어 보고
2. 학습 시작으로 종료(`training` 상태)된 경우:
   - tmux 세션 이름과 확인 방법을 다시 한 번 안내
   - "학습 완료 후 `/harness`를 다시 실행하시면 `--resume`으로 이어 진행합니다." 안내
3. Phase가 완료되었거나 여러 step이 끝났으면 **PROJ-001 동기화**로 이동

### 7. PROJ-001 동기화

활성 PROJ 문서(`projects/PROJ-*.md`)를 최신 상태로 업데이트:

1. 진행률 요약 테이블: 각 phase의 최신 status/progress 반영
2. Phase별 체크리스트: completed step은 `[x]`, training/in_progress는 `[~]`, blocked는 `[!]`, error는 `[X]`
3. 주요 리스크/이슈: 신규 blocked/error 사유 추가, 해결된 이슈는 제거
4. 변경 이력 테이블에 엔트리 추가:
   ```
   | YYYY-MM-DD | /harness 자동 동기화 — <phase-dir> 실행 결과 |
   ```

### 8. 결과 보고

```
## /harness 실행 결과

**실행 대상**: <dir>
**실행 모드**: <정상 / --resume / --dry-run / --step N>
**execute.py exit code**: <0=정상, 1=error, 2=blocked>

**상태 변화**:
  - phase-proposal: pending → training (step 3 학습 시작)
  - 또는 phase-baseline: in_progress → completed

**업데이트된 문서**:
  - PROJ-001 v<N> → v<N+1>

**다음 단계**:
  - (학습 시작된 경우) tmux: harness-<dir>-<step>. 학습 완료 후 `/harness` 재실행 → --resume
  - (blocked 발생) <phase>/step <N>: <blocked_reason>. 해결 후 status를 `pending`으로 되돌리고 /harness 재실행
  - (error 발생) /train-status로 확인 또는 수정 후 /harness 재실행
  - (완료) 다음 pending phase가 있으면 /harness 재실행, 없으면 /paper-table 또는 /update-plan
```

## blocked / error step 해결 흐름

Step 4에서 "blocked/error phase 해결"을 선택한 경우:

1. blocked·error phase와 해당 step의 `blocked_reason` / `error_message`를 표시
2. 각 항목에 대해 AskUserQuestion:
   - "수정 후 재시도" — 연구자가 설명한 수정 내용을 Claude가 반영, step status를 `pending`으로 되돌림
   - "스킵하고 `completed` 마킹" — `summary`에 `"manually skipped (YYYY-MM-DD): <이유>"` 기록 (연구자 확인 필수)
   - "로드맵 변경" — `/update-plan`으로 이동
   - "보류" — 변경 없이 종료

## 에러 처리

- **PROJ 문서 부재 / phases 빈 배열 / execute.py placeholder 미치환**: "`/setup`을 먼저 실행해 주세요." 중단
- **모든 phase completed**: "모든 phase가 완료되었습니다. `/update-plan`으로 다음 단계를 추가하거나 `/paper-table`로 결과를 정리해 주세요." 중단
- **execute.py가 exit 1**: error 상태로 종료된 step이 있다. `error_message`를 보고하고 수정 권유
- **execute.py가 exit 2**: blocked 상태로 종료된 step이 있다. `blocked_reason`을 보고하고 해결 권유
- **tmux 세션 부재 + training 상태**: "tmux 세션이 종료되었습니다. completion_check를 확인하거나 step status를 `pending`으로 되돌리고 /harness 재실행하세요."
- **현재 git 브랜치에 uncommitted changes**: execute.py가 feat 브랜치로 checkout하지 못한다. "커밋 또는 stash 후 재시도해 주세요."

## 준수 규칙

- `.claude/rules/common/safety_constraints.md` — execute.py가 자체적으로 GPU 점유 확인, tmux 사용, dry-run 플래그를 지원
- `.claude/rules/common/experiment_lifecycle.md`
- `harness/execute.py`의 MAX_RETRIES=3, TRAIN_POLL_INTERVAL=60s, TRAIN_MAX_POLL=86400s 기본값 존중
- 보고 언어: 한국어, 존댓말
