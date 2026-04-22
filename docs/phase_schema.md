# Phase / Step JSON Schema

`harness/execute.py`가 사용하는 JSON 스키마의 공식 명세입니다. `/setup`, `/harness`, `/update-plan` 커맨드는 이 스키마를 준수합니다.

## 1. Top-level Index — `projects/phases/index.json`

프로젝트 전체의 phase 목록과 상태를 추적합니다.

```json
{
  "project": "my_vision_project",
  "description": "한 문장 연구 목적",
  "phases": [
    {
      "dir": "phase-baseline",
      "name": "Baseline 모델 학습 및 평가",
      "rq": "RQ-001",
      "status": "pending",
      "progress": "0%"
    },
    {
      "dir": "phase-proposal",
      "name": "제안 방법론 구현",
      "rq": "RQ-002",
      "status": "pending"
    }
  ]
}
```

### Phase entry 필드

| 필드 | 필수 | 타입 | 설명 | 작성 주체 |
|------|------|------|------|-----------|
| `dir` | 필수 | string (unique) | Phase 디렉토리 이름. `execute.py <dir>` 호출 인자로 사용 | 사람/`/update-plan` |
| `name` | 필수 | string | Human-readable 제목 | 사람/`/update-plan` |
| `rq` | 선택 | string \| null | 관련 RQ ID (예: `"RQ-001"`). **커맨드 전용 필드** — execute.py는 읽기만 하고 쓰지 않음 | 사람/`/update-plan` |
| `status` | 필수 | enum | `pending` \| `in_progress` \| `training` \| `completed` \| `blocked` \| `error` | execute.py 자동 업데이트 |
| `progress` | 선택 | string | 예 `"60%"` | 사람 (참고용) |
| `completed_at` | 자동 | ISO8601 | Phase 완료 시각 | execute.py 자동 |
| `failed_at` | 자동 | ISO8601 | error 상태로 전환된 시각 | execute.py 자동 |
| `blocked_at` | 자동 | ISO8601 | blocked 상태로 전환된 시각 | execute.py 자동 |

### 상태 전이

```
pending ──► in_progress ──► completed
   │             │
   │             ├──► training ──► completed (학습 완료 확인 후)
   │             │
   │             ├──► error (3회 재시도 실패)
   │             │
   │             └──► blocked (사용자 개입 필요)
   │
   └──► blocked / error (직접 전이도 가능)
```

## 2. Phase-level Index — `projects/phases/<dir>/index.json`

각 phase 내부의 step 목록과 실행 상태를 추적합니다.

```json
{
  "project": "my_vision_project",
  "phase": "phase-baseline",
  "rq": "RQ-001",
  "created_at": "2026-04-22T10:00:00+0900",
  "completed_at": "2026-04-23T18:00:00+0900",
  "steps": [
    {
      "step": 0,
      "name": "config-and-dryrun",
      "type": "code",
      "status": "completed",
      "summary": "configs/baseline.yaml 작성, dry-run 통과",
      "started_at": "2026-04-22T10:00:00+0900",
      "completed_at": "2026-04-22T10:15:00+0900"
    },
    {
      "step": 1,
      "name": "train-3fold",
      "type": "train",
      "status": "training",
      "tmux_session": "harness-phase-baseline-1",
      "completion_check": "experiments/logs/baseline_3fold/training_complete.flag",
      "training_started_at": "2026-04-22T10:16:00+0900"
    }
  ]
}
```

### Top-level 필드

| 필드 | 필수 | 타입 | 설명 |
|------|------|------|------|
| `project` | 선택 | string | Top-level index의 project와 일치해야 함 |
| `phase` | 선택 | string | 설명적 이름 (dir과 동일하거나 별도) |
| `rq` | 선택 | string \| null | 관련 RQ ID |
| `steps` | 필수 | array | step entry 배열 |
| `created_at` | 자동 | ISO8601 | execute.py 최초 실행 시 기록 |
| `completed_at` | 자동 | ISO8601 | 모든 step 완료 후 기록 |

### Step entry 필드

| 필드 | 필수 | 타입 | 설명 | 작성 주체 |
|------|------|------|------|-----------|
| `step` | 필수 | integer (unique in phase) | 0부터 시작하는 step 번호 | 사람/`/update-plan` |
| `name` | 필수 | string | 예 `config-and-dryrun`, `train-3fold` | 사람/`/update-plan` |
| `type` | 필수 | enum | `code` \| `train` \| `eval` \| `analyze` | 사람/`/update-plan` |
| `status` | 필수 | enum | `pending` \| `completed` \| `error` \| `blocked` \| `training` \| `in_progress` | Claude/execute.py |
| `summary` | 선택 | string | 완료 시 한 줄 요약 | Claude (완료 시) |
| `error_message` | 선택 | string | error 상태 사유 | Claude |
| `blocked_reason` | 선택 | string | blocked 상태 사유 | Claude |
| `tmux_session` | train 필수 | string | 예 `"harness-phase-baseline-1"` | Claude |
| `completion_check` | train 필수 | string | 학습 완료 flag 파일 경로 | Claude |
| `started_at` | 자동 | ISO8601 | step 시작 시각 | execute.py |
| `completed_at` | 자동 | ISO8601 | step 완료 시각 | execute.py |
| `training_started_at` | train 자동 | ISO8601 | 학습 시작 시각 | execute.py |
| `failed_at` / `blocked_at` | 자동 | ISO8601 | | execute.py |

### Step type별 추가 규약

**code**: 코드/config 작성. `dry-run` 모드에서 `training_complete.flag`를 생성하지 말 것. 기존 checkpoint가 있으면 skip.

**train**: 학습 실행. 반드시 tmux 세션으로 백그라운드 실행. GPU 점유 확인 필수. `tmux_session`과 `completion_check`를 기록. 학습 시작 시 `status: training`으로 전환.

**eval**: 체크포인트로 평가. 결과를 `experiments/eval/`에 저장. N-fold는 mean +/- std로 요약.

**analyze**: 결과 분석, 비교표 생성, PROJ 문서 업데이트.

## 3. Step Instruction 파일 — `projects/phases/<dir>/step<N>.md`

각 step의 지시사항을 담는 markdown. execute.py가 이 파일을 읽어 Claude에게 전달합니다.

```markdown
# Step 0: Config 작성 및 Dry-run

## 작업
1. src/configs/ 에 실험 config YAML 작성
2. dry-run으로 1 epoch 학습 테스트

## Acceptance Criteria
```bash
conda run -n my_env python src/scripts/train.py --config configs/exp1.yaml --dry-run
```

## 완료 시 summary
"configs/exp1.yaml 작성, dry-run 통과 (X epoch, Y batches)"
```

## 4. Step Output — `projects/phases/<dir>/step<N>-output.json`

execute.py가 Claude를 호출한 결과를 자동 저장합니다. 직접 편집하지 마세요.

```json
{
  "step": 0,
  "name": "config-and-dryrun",
  "exitCode": 0,
  "stdout": "...",
  "stderr": "..."
}
```

## 5. Validation

JSON 유효성은 다음으로 확인:

```bash
python -c "import json; json.load(open('projects/phases/index.json'))"
python -c "import json; json.load(open('projects/phases/phase-baseline/index.json'))"
```

## 6. 커맨드별 필드 소유권

| 필드 | /setup | /update-plan | /harness | execute.py |
|------|--------|--------------|----------|------------|
| `dir`, `name`, `type`, `step` | 생성 | 변경 가능 (ID 불변) | 읽기 | 읽기 |
| `rq` | 초기값 | 변경 가능 | 읽기 | 무시 |
| `status` | `pending` 초기화 | 제한적 변경 | 읽기 | **주 소유자** |
| `summary`, `error_message`, `blocked_reason` | — | — | 읽기 | 주 소유자 |
| `tmux_session`, `completion_check` | — | — | 읽기 | 주 소유자 |
| 타임스탬프 | — | — | 읽기 | 주 소유자 |

## 7. 예시 전환 시나리오

1. `/setup` 실행 → top-level `index.json`에 5개 phase 엔트리 + 각 phase의 `index.json`을 `"steps": []`로 생성
2. `/update-plan "phase-baseline에 config, train, eval, analyze 4개 step 추가"` → phase-baseline의 `index.json`에 step 0~3 추가, step0.md~step3.md 생성
3. `/harness` → `python harness/execute.py phase-baseline` 호출
4. execute.py가 step 0 (code) 실행 → `status: completed`, `summary` 기록, git commit
5. execute.py가 step 1 (train) 실행 → tmux 세션 시작, `status: training`, `tmux_session` + `completion_check` 기록, 60초 간격 polling
6. 학습 완료 시 execute.py가 `completion_check` 파일 존재를 확인 → `status: completed`
7. 이후 step 2 (eval), step 3 (analyze) 자동 진행
8. 모든 step `completed` → phase `status: completed`, top-level index에도 반영, `/harness`가 PROJ-001 동기화
