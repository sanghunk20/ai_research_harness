# Repository Structure

```
{project}/
├── notes/                 # 연구 문서
│   ├── thinking/          # 자유로운 생각, 브레인스토밍
│   ├── concepts/          # CON-XXX: 개념 정의
│   ├── research_questions/# RQ-XXX: 연구 질문
│   ├── decisions/         # DEC-XXX: 결정 기록
│   └── references/        # REF-[Name]: 논문 리뷰 노트
├── projects/              # 프로젝트 추적
│   └── phases/            # Phase JSON 상태 추적
│       ├── index.json     # 전체 phase 현황
│       └── phase-X/       # 각 phase별 step 관리
├── experiments/           # 실험 결과
│   ├── logs/              # EXP-YYYYMMDD-XX 문서
│   └── eval/              # 평가 결과 (체크포인트, 메트릭)
├── src/                   # 코드
│   ├── {package}/         # 메인 패키지
│   ├── scripts/           # Shell scripts
│   └── ...
├── data/                  # [gitignored] 작업 데이터셋
├── data_backup/           # [gitignored] 읽기 전용 백업
├── templates/             # 노트 템플릿
├── harness/               # 실험 실행 엔진
│   └── execute.py
└── .claude/               # 하네스 설정
    ├── rules/common/      # AI 연구 공통 규칙
    ├── rules/domain/      # 도메인 전용 규칙
    ├── hooks/             # 안전 hooks
    └── commands/          # 커스텀 커맨드
```

## 노트 폴더 역할 분리

| 폴더 | 역할 | 내용 |
|------|------|------|
| `notes/research_questions/` | **What** — 질문 자체 | RQ 번호 + 질문 1~2문장 |
| `notes/concepts/` | **Why & How** — 배경, 동기, 실험 설계 | CON 문서에 RQ별 배경+설계 |
| `notes/decisions/` | **Result** — 결론 | 실험 결과 기반 결정사항 |
| `projects/` | **Status** — 진행 상황 | 상태 추적, 계획표 |
