ai_research_harness를 새 프로젝트에 맞게 초기 세팅하라. Git clone 직후 1회만 실행한다. CLAUDE.md placeholder 치환, 연구 목적/방법론/로드맵 구체화, 초기 문서 부트스트랩까지 수행한다.

## 전제 조건 확인

### 1. 중복 실행 방지

다음 중 하나라도 이미 존재하면 setup이 완료된 것으로 간주:
- `projects/.setup_done` 마커 파일
- `projects/PROJ-*.md` 파일 (glob 매칭)

존재하면 AskUserQuestion으로:
> "이미 setup이 완료된 프로젝트로 보입니다. 기존 설정을 덮어쓰고 재실행할까요? (기존 PROJ/RQ/CON 문서가 영향받을 수 있습니다)"

거부 선택 시 중단.

### 2. 작업 디렉토리 확인

`pwd`로 현재 디렉토리가 ai_research_harness 루트(`CLAUDE.md`, `harness/`, `projects/`가 있는 곳)인지 확인.

## 실행 절차 (대화형)

AskUserQuestion을 적극 활용한다. 섹션별로 관련 질문을 묶어서 한 번에 물어보고, 한 번에 너무 많은 질문을 던지지 말 것. 자동 감지 가능한 값은 기본값으로 먼저 제시하고 수정 여부만 확인.

### Section 1. 연구 목적 구체화

AskUserQuestion:
1. **프로젝트명** (영문 snake_case, 예: `cephalometric_landmark`)
2. **한 문장 연구 목적** — 예: "치아 교정 진단용 측모 두부계측 landmark를 자동 검출"
3. **도메인** — 선택지: medical imaging / autonomous driving / industrial vision / remote sensing / general vision / 기타(자유 입력)
4. **Vision task type** — 선택지: classification / detection / segmentation / landmark / pose estimation / generation / multi-task / 기타
5. **최종 output 형태** — 선택지: 학술 논문 / 기술 리포트 / 프로덕션 모델 / 복수

### Section 2. 연구 방법론 구체화

Task type에 맞춰 질문 조정:

1. **입력 형태**: 이미지 shape (예: `1024×1024`), 채널 수, 시퀀스/3D 여부
2. **출력 형태**: task 별 — class 수 / bbox+class / mask resolution / landmark 수 / 생성 이미지 해상도 등
3. **파이프라인 개요** — 한 줄 기술. 예: `ImageNet pretrained backbone → landmark regression head → fine-tuning`
4. **Baseline 모델 후보 (2~4개)** — 예: `ResNet50, ViT-B/16, Swin-T, ConvNeXt-T`. 이후 REF 노트 작성 대상으로 기록
5. **검증 전략** — 선택지: single train/val/test / K-fold (K=?) / Leave-One-Out / stratified / 기타
6. **평가 메트릭** — task별 기본값 제안 후 커스텀 허용:
   - classification: Top-1 Acc, F1, AUC
   - detection: mAP@0.5, mAP@0.5:0.95
   - segmentation: mIoU, Dice
   - landmark: MRE (mm 또는 pixel), SDR@(2/3/4)mm 또는 PCK
   - pose estimation: PCK, AP
   - generation: FID, IS, LPIPS

### Section 3. 환경 설정

자동 감지 우선:

1. **Conda 환경명**
   ```bash
   conda info --envs | awk '/\*/ {print $1}'
   ```
   감지된 활성 env를 기본값으로 제시. 없으면 새 이름 요청.
2. **GPU 구성** 자동 감지:
   ```bash
   nvidia-smi --query-gpu=index,name,memory.total --format=csv,noheader 2>/dev/null
   ```
   결과 기반으로 `{GPU_SPEC}` 초안 (예: `H100 x 2`) 제시 후 수정 가능.
3. **Precision** — 선택지: fp32 / fp16 AMP / bfloat16 AMP
   - 감지된 GPU가 H100/A100/Ada 세대면 **bfloat16 AMP**를 기본값으로 제시
   - 구형(V100, T4 등)이면 **fp16 AMP**를 기본값으로
4. **학습 실행 사용자 (TRAIN_USER)** — 공유 서버에서 `sudo -u <user>`로 학습을 실행할 사용자명
   - 자동 감지: `whoami`
   - 단일 사용자 환경이면 `None` (빈 문자열) 허용 — 이 경우 `sudo` 래핑을 하지 않음
5. **실험 추적 백엔드** — 선택지: `tensorboard` / `wandb` / `none`
   - 기본값: `tensorboard` (로컬 파일, 외부 서비스 의존성 없음)
   - `wandb` 선택 시 추가 수집:
     - **WandB entity** (team 또는 username)
     - **WandB project** — 기본값은 Section 1.1의 프로젝트명
     - **API key는 수집·저장하지 않는다.** 연구자에게 다음 안내:
       > "학습 실행 전 `export WANDB_API_KEY=<key>`를 쉘 환경변수로 설정하거나 `wandb login`을 한 번 실행해 주세요. `/setup`은 API key를 파일에 저장하지 않습니다."

### Section 4. 데이터 설정

1. **데이터 경로 확인**
   ```bash
   ls -la data/ data_backup/ 2>/dev/null
   ```
   없으면 빈 디렉토리 생성 여부 질문 (`data_backup/`은 읽기 전용 백업이므로 생성만 하고 내용은 연구자가 수동 배치).
2. **데이터셋 구조 기술** (자유 입력 한 단락) — PROJ 문서에 그대로 삽입됨
3. **Train/Val/Test split 전략** — split 파일 경로 또는 on-the-fly 분할 규칙

### Section 5. 연구 로드맵 작성

기본 제안 (vision 연구 일반) — 연구자가 수정/추가/삭제 가능:

1. `phase-baseline` — Baseline 모델 학습 및 평가 (RQ-001)
2. `phase-analysis` — 에러 분석, 데이터 분석
3. `phase-proposal` — 제안 방법론 구현 및 비교
4. `phase-ablation` — Ablation study
5. `phase-extension` — 추가 실험 (선택)

AskUserQuestion으로:
- Phase 구조 (추가/삭제/이름 변경)
- 각 Phase의 `rq` (없으면 null)
- 각 Phase의 한 줄 목적

### Section 6. 적용 Preview 및 확인

모든 변경 내역을 요약해서 제시한 뒤 AskUserQuestion으로 최종 "진행/수정/취소" 확인. 취소 시 어떤 파일도 수정하지 말 것.

### Section 7. 파일 생성/수정 적용

#### 7.1 CLAUDE.md / harness / hooks placeholder 치환

**CLAUDE.md** — 다음 9개 placeholder를 Section 1-3 입력값으로 치환 (Edit 도구 사용, 이미 치환된 항목은 건드리지 말 것):
- `{PROJECT_NAME}` ← Section 1.1
- `{RESEARCH_GOAL}` ← Section 1.2
- `{DOMAIN}` ← Section 1.3 (task type 포함해서 구체화)
- `{PIPELINE}` ← Section 2.3
- `{VALIDATION}` ← Section 2.5
- `{METRICS}` ← Section 2.6 (쉼표로 구분)
- `{CONDA_ENV}` ← Section 3.1
- `{GPU_SPEC}` ← Section 3.2
- `{PRECISION}` ← Section 3.3

**`projects/phases/index.json`의 top-level** — 기존 placeholder 치환:
- `{PROJECT_NAME}` ← Section 1.1
- `{PROJECT_DESCRIPTION}` ← Section 1.2

**`harness/execute.py`** — 파일 상단 설정 상수 치환 (Edit 도구):
- `CONDA_ENV = "{CONDA_ENV}"` ← Section 3.1 입력값 (따옴표 유지)
- `TRAIN_USER = "{TRAIN_USER}"` ← Section 3.4 입력값 (단일 사용자 환경이면 `None` — 따옴표 제거)

**`.claude/hooks/safety_guard.sh`** — `PROJECT_ROOT` 변수 치환:
- 2번째 줄 `PROJECT_ROOT=""` → `PROJECT_ROOT="<현재 프로젝트 절대경로>"` (`pwd` 결과)
- 이미 값이 채워져 있으면 건드리지 말고 기존 값 유지

#### 7.2 projects/phases/index.json 업데이트

`harness/execute.py`가 사용하는 top-level 스키마로 작성 (자세한 스키마는 `docs/phase_schema.md` 참조):

```json
{
  "project": "<PROJECT_NAME>",
  "description": "<Section 1.2>",
  "phases": [
    {
      "dir": "phase-baseline",
      "name": "Baseline 모델 학습 및 평가",
      "rq": "RQ-001",
      "status": "pending",
      "progress": "0%"
    }
  ]
}
```

필드 요약:
- `dir` (필수, unique) — phase 디렉토리 이름, execute.py 호출 인자로도 사용됨
- `name` (필수) — human-readable
- `rq` (선택, null 허용) — 관련 RQ ID (`/harness`, `/update-plan`이 사용, execute.py는 무시)
- `status` (필수) — `pending` | `in_progress` | `training` | `completed` | `blocked` | `error`
- `progress` (선택) — 문자열 `"0%"` 형태

#### 7.3 Phase별 index.json 생성

각 Phase에 대해 `projects/phases/<dir>/index.json`:

```json
{
  "project": "<PROJECT_NAME>",
  "phase": "<dir>",
  "rq": "<RQ or null>",
  "status": "pending",
  "steps": []
}
```

Step을 추가할 때의 표준 필드(execute.py가 기대하는 형식):
- `step` (필수, 정수) — 0부터 시작하는 step 번호
- `name` (필수) — 예: `config-and-dryrun`
- `type` (필수) — `code` | `train` | `eval` | `analyze`
- `status` (필수) — `pending` | `completed` | `error` | `blocked` | `training` | `in_progress`
- `summary` (선택, 완료 시) — 한 줄 요약
- `error_message` / `blocked_reason` (선택)
- `tmux_session` / `completion_check` (train step용) — 예: `"harness-phase-baseline-1"` / `"experiments/logs/.../training_complete.flag"`
- `started_at` / `completed_at` / `training_started_at` 등 타임스탬프는 execute.py가 자동 기록

Setup 단계에서는 `steps`를 빈 배열로 두고, 이후 `/update-plan`으로 step을 추가한다.

#### 7.4 PROJ-001 진행 현황 문서 생성

경로: `projects/PROJ-001_<project_name>_progress.md`

```markdown
---
id: PROJ-001
title: <프로젝트명> — 진행 현황
created: <YYYY-MM-DD>
version: v1.0
---

# PROJ-001: <프로젝트명>

## 1. 연구 개요
- **목적**: <Section 1.2>
- **도메인**: <Section 1.3>
- **Task**: <Section 1.4>
- **최종 output**: <Section 1.5>

## 2. 방법론 요약
- **입력**: <Section 2.1>
- **출력**: <Section 2.2>
- **파이프라인**: <Section 2.3>
- **Baseline**: <Section 2.4>
- **검증**: <Section 2.5>
- **메트릭**: <Section 2.6>
- **실험 추적**: <Section 3.5> (wandb인 경우 entity/project 함께 기록)
- **Seed / 재현성**: seed 값은 config.experiment.seed에 기록. Reproducibility 규칙은 `.claude/rules/common/reproducibility.md` 준수

## 3. 데이터
<Section 4.2>

- split 전략: <Section 4.3>

## 4. 진행률 요약

| Phase | RQ | 상태 | 진행률 |
|-------|----|------|--------|
| phase-baseline | RQ-001 | pending | 0% |
| ... | ... | pending | 0% |

## 5. Phase별 체크리스트

### phase-baseline
- [ ] (추후 step 추가: `/update-plan`)

...

## 6. 주요 리스크 및 이슈

(없음)

## 7. 변경 이력

| 날짜 | 내용 |
|------|------|
| <YYYY-MM-DD> | v1.0 — 초기 setup (by /setup) |
```

#### 7.5 초기 RQ-001 생성

경로: `notes/research_questions/RQ-001.md`

```markdown
---
id: RQ-001
title: <Section 1.2를 질문 형태로 변환>
created: <YYYY-MM-DD>
status: active
---

# RQ-001: <질문>

<Section 1.2 기반 1~2문장 연구 질문>

## 관련 Phase
- phase-baseline

## 관련 문서
- [CON-001](../concepts/CON-001_strategy.md)
- [PROJ-001](../../projects/PROJ-001_<project_name>_progress.md)
```

#### 7.6 초기 CON-001 생성

경로: `notes/concepts/CON-001_strategy.md`

```markdown
---
id: CON-001
title: <프로젝트명> 연구 전략
created: <YYYY-MM-DD>
version: v1.0
related_rqs: [RQ-001]
---

# CON-001: 연구 전략

## 1. 배경
(연구자 보완 필요)

## 2. 핵심 가설
<Section 1.2 기반 — "X하면 Y가 개선될 것이다" 형태로 전환>

## 3. 방법론
- **Baseline**: <Section 2.4>
- **파이프라인**: <Section 2.3>
- **검증**: <Section 2.5>
- **메트릭**: <Section 2.6>

## 4. Baseline 비교 대상
- (REF 노트 작성 예정): <Section 2.4에서 나열된 모델들>

## 5. 기여 (Contributions)
1. (연구자 보완 필요)

## 6. 변경 이력

| 날짜 | 내용 |
|------|------|
| <YYYY-MM-DD> | v1.0 — 초기 setup (by /setup) |
```

#### 7.7 .gitignore 점검

다음 항목 누락 시 추가:
```
data/
data_backup/
experiments/logs/*/checkpoints/
experiments/logs/*/training_complete.flag
experiments/eval/
__pycache__/
*.pyc
.claude/settings.local.json
```

기존 `.gitignore`를 읽어 중복 방지.

#### 7.8 안전 hook 등록 확인

기존 `.claude/hooks/safety_guard.sh`가 이미 `data_backup/`·프로젝트 외부 경로·`rm -rf`·`git push --force`·`git reset --hard`를 차단한다. Setup은 이 파일의 `PROJECT_ROOT`만 채우고(7.1에서 수행), 아래 등록 상태만 확인한다.

```bash
cat .claude/settings.json 2>/dev/null | grep -o 'safety_guard.sh' || echo "not registered"
```

`.claude/settings.json`에 `safety_guard.sh`가 `PreToolUse` hook으로 등록되어 있지 않으면 `update-config` 스킬을 호출하여 다음을 추가한다 (기존 설정 병합):

- **이벤트**: `PreToolUse`
- **matcher**: `Write|Edit|Bash|NotebookEdit`
- **command**: `bash .claude/hooks/safety_guard.sh`

> 추가 hook을 새로 만들지 않는다. `data/`는 설계상 "작업 디렉토리"로 수정이 허용되고, `data_backup/`만 엄격 보호된다는 기존 정책을 유지한다.

#### 7.9 CLAUDE.md에 PROJ-001 참조 및 agent 작업 지침 삽입

CLAUDE.md의 "프로젝트 진행 현황" 섹션을 찾아 기존 블록:

```
세션 시작 시 반드시 확인:
@./projects/phases/index.json
```

을 다음으로 교체한다:

```
세션 시작 시 반드시 이 순서대로 확인:
@./projects/PROJ-001_<PROJECT_NAME>_progress.md
@./projects/phases/index.json

세션 시작 시 AI agent는 위 문서로부터 다음을 파악하여 연구자에게 보고:
1. 현재 활성 phase와 진행률
2. 다음 pending step의 유형과 목적
3. blocked step이 있으면 그 이유
4. 작업 재개 제안 — 일반적으로 `/harness`를 호출하여 진행 위치부터 이어서 수행

AI agent는 PROJ-001의 로드맵과 `phases/index.json`의 현재 step 상태를 기준으로 연구를 설계·진행한다. 연구 방향이 로드맵과 충돌하면 독자적으로 변경하지 말고 `/update-plan`을 통해 연구자 확인을 받는다.
```

`<PROJECT_NAME>`은 Section 1.1에서 입력받은 값으로 치환한다.

### 8. Smoke Test (검증)

모든 생성 파일에 대해:
```bash
python -c "import json; json.load(open('projects/phases/index.json'))"
```
각 phase별 `index.json`도 동일하게 검증.

CLAUDE.md에 남은 `{...}` placeholder가 없는지 grep으로 확인:
```bash
grep -n '{[A-Z_]*}' CLAUDE.md
```
남아 있으면 경고 출력.

### 9. 완료 마커

`projects/.setup_done` 파일 생성 (1줄, 형식: `<YYYY-MM-DD> <project_name>`).

### 10. 결과 보고

```
## Setup 완료

**프로젝트**: <PROJECT_NAME>
**도메인**: <DOMAIN>
**Task**: <TASK_TYPE>
**환경**: conda `<CONDA_ENV>` / <GPU_SPEC> / <PRECISION>

**치환된 설정**:
- CLAUDE.md placeholder 9개
- harness/execute.py: CONDA_ENV, TRAIN_USER
- .claude/hooks/safety_guard.sh: PROJECT_ROOT
- projects/phases/index.json: project, description

**생성된 문서**:
- projects/PROJ-001_<name>_progress.md
- notes/research_questions/RQ-001.md
- notes/concepts/CON-001_strategy.md

**생성된 Phase 구조**:
- projects/phases/index.json (<N>개 phase 등록)
- projects/phases/<dir>/index.json (<N>개, steps는 빈 배열로 시작)

**Baseline REF 노트 작성 대상**:
- <Section 2.4의 모델 목록>

**다음 할 일**:
1. CON-001 본문 보완 (배경, 기여 구체화)
2. Baseline REF 노트 작성: `notes/references/REF-<Name>.md` (원논문 검증 후 `source_verified: true`)
3. `data/`에 데이터 배치
4. (wandb 선택 시) 쉘에서 `export WANDB_API_KEY=<key>` 또는 `wandb login` 1회 실행
5. 로드맵 진행: `/harness` (현재 위치 파악 후 일괄 진행) 또는 `/train phase-baseline` (단일 step 실행)
6. 계획 수정이 필요하면: `/update-plan <자연어 설명>`
```

## 에러 처리

- **CLAUDE.md placeholder 일부가 이미 치환됨**: "이미 치환된 값이 있습니다. 현재 값: ... 덮어쓸까요?" 로 항목별 확인
- **conda env 부재**: "환경 `<name>`이 없습니다. 먼저 `conda create -n <name> python=3.x`를 실행해 주세요." (setup이 직접 생성하지 않음 — 권한/정책 문제 회피)
- **GPU 미감지**: "GPU가 감지되지 않습니다. CPU 전용 모드로 진행할까요?" 컨펌
- **data/ 없음**: 빈 디렉토리 생성 (데이터는 연구자가 수동 배치)
- **PROJ 문서가 이미 존재**: Step 1의 중복 실행 방지로 이미 차단됨

## 준수 규칙

- `.claude/rules/common/safety_constraints.md` (프로젝트 외부 경로 수정 금지, `data_backup/` 수정 금지)
- `.claude/rules/common/id_system.md` (ID 1회 부여 후 변경 금지)
- CLAUDE.md 소통 스타일: 한국어, 존댓말, 아부 금지
- setup은 **파괴적 재실행 금지** — 중복 실행 방지 체크 필수
