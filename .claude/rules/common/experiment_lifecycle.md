# 실험 생명주기 프로토콜 (AI 연구 공통)

## 실험 단계

```
설계 (Design) → 구현 (Code) → 검증 (Dry-run) → 학습 (Train) → 평가 (Eval) → 분석 (Analyze)
```

### 1. 설계 (Design)
- 가설 명시: "X하면 Y가 개선될 것이다"
- 독립/종속 변수 정의
- Baseline 대비 비교 기준 설정
- EXP 문서 작성

### 2. 구현 (Code)
- Config YAML 작성
- 기존 코드와의 일관성 유지
- 코드 리뷰 프로토콜 수행

### 3. 검증 (Dry-run)
- 1 epoch, 1 GPU, fold 0으로 테스트
- OOM 체크, gradient flow 확인
- dry-run에서 training_complete.flag 생성 금지

### 4. 학습 (Train)
- 기존 checkpoint skip 로직 포함
- tmux 세션으로 실행
- 공유 서버: GPU 점유 확인 후 컨펌

### 5. 평가 (Eval)
- 결과를 mean +/- std 형식으로 보고
- 시각화는 평가 시에만 생성

### 6. 분석 (Analyze)
- N-fold: mean +/- std
- 프로젝트 문서 업데이트

## Phase/Step JSON 추적

모든 실험은 `projects/phases/`에서 JSON으로 상태 추적:
- `index.json`: 전체 phase 현황
- `phase-X/index.json`: phase 내 step별 상태

Step 유형:
| type | 설명 | 실행 주체 |
|------|------|----------|
| code | 코드 작성, config, shell script | Claude (execute.py) |
| train | 모델 학습, DDP | Claude (tmux 백그라운드) |
| eval | checkpoint 평가, metric 계산 | Claude (execute.py) |
| analyze | 결과 비교, 테이블, 문서 업데이트 | Claude (execute.py) |
