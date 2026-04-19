# Research Harness — {PROJECT_NAME}
# Claude Code는 작업 시작 전 반드시 이 파일 전체를 읽을 것

---

## 연구 개요

- **목표**: {RESEARCH_GOAL}
- **도메인**: {DOMAIN}
- **파이프라인**: {PIPELINE — e.g., ImageNet pretrained backbone → fine-tuning}
- **검증**: {VALIDATION — e.g., 3-fold cross-validation}
- **메트릭**: {METRICS — e.g., MRE (mm), SDR@2mm / 3mm / 4mm}

---

## 디렉토리 구조

```
{project}/
├── notes/                    # 연구 문서
│   ├── thinking/             # 자유로운 생각, 브레인스토밍
│   ├── concepts/             # CON-XXX: 개념 정의
│   ├── research_questions/   # RQ-XXX: 연구 질문
│   ├── decisions/            # DEC-XXX: 결정 기록
│   └── references/           # REF-[Name]: 논문 리뷰 노트
├── projects/                 # 프로젝트 추적
│   └── phases/               # Phase JSON 상태 추적
├── experiments/              # 실험 결과
│   ├── logs/                 # EXP-YYYYMMDD-XX 문서
│   └── eval/                 # 평가 결과
├── src/                      # 코드
│   ├── {package}/            # 메인 패키지
│   ├── scripts/              # Shell scripts
│   └── ...
├── data/                     # [gitignored] 작업 데이터셋
├── data_backup/              # [gitignored] 읽기 전용 백업
├── templates/                # 노트 템플릿
├── harness/                  # 실험 실행 엔진
│   └── execute.py
└── .claude/                  # 하네스 설정
    ├── rules/common/         # AI 연구 공통 규칙
    ├── rules/domain/         # 도메인 전용 규칙
    ├── hooks/                # 안전 hooks
    └── commands/             # 커스텀 커맨드
```

---

## 환경 설정

```bash
conda activate {CONDA_ENV}
{추가 환경 설정}
```

- GPU: {GPU_SPEC}
- Precision: {PRECISION — e.g., bfloat16 AMP}

---

## 운영 규칙

### 절대 금지
- `data/`, `data_backup/` 무단 수정 금지 (hooks로 보호됨)
- rm -rf 사용 금지
- 프로젝트 외부 경로 수정 금지

### 결과 보고 형식
- N-fold 결과: **mean ± std** 형식
- 보고 언어: 한국어

---

## 현재 진행 상황
<!-- 최종 업데이트: {DATE} -->

### 완료된 실험
- [ ] {실험 1}

### 진행 중인 실험
- [ ] {실험 2}

### 다음 실험
- [ ] {실험 3}

---

## 참고
- Phase 상태 추적: `projects/phases/index.json`
- 하네스 실행: `python harness/execute.py <phase-dir>`
