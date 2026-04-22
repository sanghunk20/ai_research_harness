# AI Research Harness

Claude Code 기반 AI 연구 자동화 프레임워크. Medical AI / Computer Vision 연구를 위한 재사용 가능한 하네스 템플릿.

## 특징

- **Phase/Step 실행 엔진** — `execute.py`로 실험 단계를 자동 순차 실행
- **학습 자동화** — tmux 백그라운드 학습, GPU 점유 확인, 공유 서버 안전 장치
- **JSON 상태 추적** — Phase/Step 진행 상황을 JSON으로 관리
- **안전 장치** — 프로젝트 외부 수정 차단, rm -rf 차단, 데이터 보호 hooks
- **재사용 가능한 규칙** — AI 연구 공통 프로토콜 (실험 생명주기, 코드 리뷰, baseline 구현 등)

## 시작하기 (Quickstart)

### 1. 템플릿 clone

```bash
git clone https://github.com/sanghunk20/ai_research_harness.git my_project
cd my_project
rm -r .git && git init  # 새 git 히스토리 시작
```

### 2. `/setup` 한 번으로 초기화

Claude Code 안에서:

```
/setup
```

대화식으로 다음을 수행합니다:
- 연구 목적·방법론·로드맵 구체화 (AskUserQuestion)
- CLAUDE.md placeholder 9개 + `harness/execute.py`의 `CONDA_ENV`/`TRAIN_USER` + `.claude/hooks/safety_guard.sh`의 `PROJECT_ROOT` 자동 치환
- `projects/phases/index.json` 및 phase별 `index.json` 생성
- 초기 `PROJ-001`, `RQ-001`, `CON-001` 문서 부트스트랩
- `.gitignore` 점검, `safety_guard.sh` hook 등록 확인

수동 편집은 필요 없습니다. 치환된 값이 마음에 들지 않으면 해당 파일을 직접 편집하거나 `/update-plan`을 사용합니다.

### 3. 로드맵 이어가기 — `/harness`

```
/harness
```

- 현재 로드맵상 **다음 실행할 phase**를 자동 선정
- `python harness/execute.py <phase-dir>` 또는 `--resume`을 호출
- train step은 tmux 백그라운드, 학습 완료는 자동 polling
- blocked/error는 연구자에게 보고 후 해결 흐름 제시

### 4. 계획 변경 — `/update-plan`

```
/update-plan "phase-baseline에 ablation step 3개 추가"
```

- 변경을 경량/중간/중대로 분류
- 영향받는 PROJ / phases JSON / CON / RQ / DEC 문서를 Preview 후 일괄 수정
- 중대 변경 시 DEC 초안 자동 생성

### 5. 템플릿 활용

`templates/` 디렉토리에 EXP/REF 노트, train config YAML, vision 공통 `dataset_base.py` / `trainer_base.py`, task 예시(`classification_task.py`)가 있습니다. 자세한 사용법은 `templates/README.md` 참조.

### 6. Phase 구조 이해

Phase/Step JSON의 공식 스키마는 `docs/phase_schema.md` 참조. 수동으로 작성하려면:

```bash
mkdir -p projects/phases/phase-exp1

cat > projects/phases/phase-exp1/index.json << 'EOF'
{
  "project": "my_project",
  "phase": "phase-exp1",
  "rq": "RQ-001",
  "status": "pending",
  "steps": [
    {"step": 0, "name": "config-and-dryrun", "type": "code",    "status": "pending"},
    {"step": 1, "name": "training",          "type": "train",   "status": "pending"},
    {"step": 2, "name": "evaluation",        "type": "eval",    "status": "pending"},
    {"step": 3, "name": "analysis",          "type": "analyze", "status": "pending"}
  ]
}
EOF

cat > projects/phases/phase-exp1/step0.md << 'EOF'
# Step 0: Config 작성 및 Dry-run
...
EOF

python harness/execute.py phase-exp1
```

같은 동작을 `/update-plan`으로 자동화할 수 있습니다.

## 커스텀 커맨드 요약

Claude Code 안에서 사용:

| 커맨드 | 용도 |
|---|---|
| `/setup` | Git clone 후 1회 실행. 연구 목적/방법론/로드맵 구체화 + placeholder 자동 치환 + 초기 문서 부트스트랩 |
| `/harness` | 현재 로드맵상 다음 phase를 자동 선정하여 `harness/execute.py`로 실행. 재개/dry-run/상태확인 선택 가능 |
| `/update-plan <자연어 설명>` | 계획 변경을 영향받는 PROJ/phases/CON/RQ 문서에 일괄 반영. 중대 변경 시 DEC 초안 자동 생성 |
| `/train [phase-dir]` | 단일 phase의 다음 step만 실행 (legacy; 일반적으로 `/harness` 권장) |
| `/train-status` | 학습 세션/GPU/phase 상태 확인 |
| `/paper-table` | 실험 결과를 논문용 LaTeX 테이블로 변환 |

## Shell 사용법 (execute.py 직접 호출)

```bash
# Phase 순차 실행
python harness/execute.py phase-exp1

# 학습 완료 후 재개
python harness/execute.py phase-exp1 --resume

# 특정 step만 실행
python harness/execute.py phase-exp1 --step 2

# 실행 계획 확인
python harness/execute.py phase-exp1 --dry-run

# Phase 상태 확인
python harness/execute.py phase-exp1 --status

# 모든 phase 상태
python harness/execute.py --status-all
```

## Step 유형

| Type | 설명 | 실행 방식 |
|------|------|----------|
| `code` | 코드/config 작성 | Claude가 직접 실행 |
| `train` | 모델 학습 | tmux 백그라운드 + GPU 점유 확인 |
| `eval` | 평가 | Claude가 직접 실행 |
| `analyze` | 결과 분석 | Claude가 직접 실행 |

## 디렉토리 구조

```
my_project/
├── notes/                    # 연구 문서
│   ├── thinking/             # 브레인스토밍
│   ├── concepts/             # CON-XXX
│   ├── research_questions/   # RQ-XXX
│   ├── decisions/            # DEC-XXX
│   └── references/           # REF-[Name]
├── projects/                 # 프로젝트 추적
│   ├── PROJ-001_*.md         # 진행 현황 (by /setup)
│   └── phases/               # Phase JSON 상태
├── experiments/              # 실험 결과
│   ├── logs/                 # EXP 문서
│   └── eval/                 # 평가 결과
├── src/                      # 코드
├── data/                     # [gitignored] 데이터셋
├── data_backup/              # [gitignored] 읽기 전용 백업
├── harness/                  # 실행 엔진
│   └── execute.py
├── templates/                # EXP/REF 템플릿 + Vision 코드 skeleton
├── docs/
│   └── phase_schema.md       # Phase/Step JSON 공식 스키마
└── .claude/                  # 하네스 설정
    ├── rules/common/         # AI 연구 공통 규칙
    ├── rules/domain/         # 도메인 전용 규칙
    ├── hooks/                # 안전 hooks (safety_guard.sh)
    └── commands/             # 커스텀 커맨드 (setup/harness/update-plan 등)
```

## 안전 장치

- **프로젝트 외부 수정 차단** — hooks가 프로젝트 루트 외부 파일 수정을 차단
- **rm -rf 차단** — 위험 명령어 자동 차단
- **데이터 보호** — `data_backup/` 수정 불가
- **GPU 점유 확인** — 공유 서버에서 다른 사용자 프로세스 감지 시 컨펌 요청
- **삭제 컨펌** — 파일 삭제 시 연구자 승인 필수

## Credits

- Adapted from [harness_framework](https://github.com/jha0313/harness_framework)
- Built for use with [Claude Code](https://claude.ai/claude-code)
