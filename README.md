# AI Research Harness

Claude Code 기반 AI 연구 자동화 프레임워크. Medical AI / Computer Vision 연구를 위한 재사용 가능한 하네스 템플릿.

## 특징

- **Phase/Step 실행 엔진** — `execute.py`로 실험 단계를 자동 순차 실행
- **학습 자동화** — tmux 백그라운드 학습, GPU 점유 확인, 공유 서버 안전 장치
- **JSON 상태 추적** — Phase/Step 진행 상황을 JSON으로 관리
- **안전 장치** — 프로젝트 외부 수정 차단, rm -rf 차단, 데이터 보호 hooks
- **재사용 가능한 규칙** — AI 연구 공통 프로토콜 (실험 생명주기, 코드 리뷰, baseline 구현 등)

## 시작하기

### 1. 템플릿 clone

```bash
git clone https://github.com/sanghunk20/ai_research_harness.git my_project
cd my_project
rm -r .git && git init  # 새 git 히스토리 시작
```

### 2. 프로젝트 설정

**CLAUDE.md** 편집 — `{PROJECT_NAME}`, `{RESEARCH_GOAL}`, `{DOMAIN}` 플레이스홀더 채우기

**AGENTS.md** 편집 — 프로젝트 환경, 진행 상황 업데이트

**harness/execute.py** 상단 설정:
```python
CONDA_ENV = "my_env"           # conda 환경명
TRAIN_USER = "username"        # 학습 실행 사용자 (sudo 필요 시)
PHASES_DIR = ROOT / "projects" / "phases"
```

**`.claude/hooks/safety_guard.sh`** — `PROJECT_ROOT` 설정

### 3. 도메인 규칙 추가

`.claude/rules/domain/`에 프로젝트 전용 규칙 추가:
```
.claude/rules/domain/
├── domain_terms.md          # 도메인 용어 정의
├── technical_details.md     # 기술 세부사항
└── baseline_references.md   # Baseline 논문 참조
```

### 4. Phase 생성 및 실행

```bash
# Phase 디렉토리 생성
mkdir -p projects/phases/phase-exp1

# index.json 작성
cat > projects/phases/phase-exp1/index.json << 'EOF'
{
  "project": "my_project",
  "phase": "experiment-1",
  "steps": [
    {"step": 0, "name": "config-and-dryrun", "type": "code",    "status": "pending"},
    {"step": 1, "name": "training",          "type": "train",   "status": "pending"},
    {"step": 2, "name": "evaluation",        "type": "eval",    "status": "pending"},
    {"step": 3, "name": "analysis",          "type": "analyze", "status": "pending"}
  ]
}
EOF

# Step 파일 작성 (각 step의 지시사항)
cat > projects/phases/phase-exp1/step0.md << 'EOF'
# Step 0: Config 작성 및 Dry-run

## 작업
1. src/configs/에 실험 config YAML 작성
2. dry-run으로 1 epoch 학습 테스트

## Acceptance Criteria
```bash
conda run -n my_env python src/scripts/train.py --config configs/exp1.yaml --dry-run
```
EOF

# 실행
python harness/execute.py phase-exp1
```

## 사용법

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
│   └── phases/               # Phase JSON 상태
├── experiments/              # 실험 결과
│   ├── logs/                 # EXP 문서
│   └── eval/                 # 평가 결과
├── src/                      # 코드
├── data/                     # [gitignored] 데이터셋
├── data_backup/              # [gitignored] 읽기 전용 백업
├── harness/                  # 실행 엔진
│   └── execute.py
└── .claude/                  # 하네스 설정
    ├── rules/common/         # AI 연구 공통 규칙
    ├── rules/domain/         # 도메인 전용 규칙
    ├── hooks/                # 안전 hooks
    └── commands/             # 커스텀 커맨드
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
