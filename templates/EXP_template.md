---
id: EXP-YYYYMMDD-XX
title: <실험 제목>
date: <YYYY-MM-DD>
phase: <phase-dir>
rq: <RQ-XXX>
status: draft | running | completed | failed
---

# EXP-YYYYMMDD-XX: <실험 제목>

## 1. 가설
<X하면 Y가 개선될 것이다. Baseline 대비 Z 정도.>

## 2. 독립 변수 / 종속 변수
- **독립 변수**: <바꾸는 것>
- **종속 변수**: <측정하는 것>
- **통제 변수**: <고정하는 것>

## 3. 실험 설정
- **Baseline**: <모델/기법 + 출처 (REF-XXX)>
- **데이터**: <데이터셋 이름, split>
- **검증**: <single / K-fold, K=?>
- **환경**: conda `<CONDA_ENV>`, GPU `<GPU_SPEC>`, precision `<PRECISION>`
- **Config 경로**: `src/configs/<config_name>.yaml`
- **Checkpoint 경로**: `experiments/logs/<exp_id>/`
- **Seed**: <seed 값>

## 4. 수행 절차
1. Dry-run 통과 확인
2. tmux 세션에서 학습 (`harness-<phase>-<step>`)
3. 평가 스크립트 실행 → `experiments/eval/<exp_id>/`
4. 분석 및 비교

## 5. 결과
### 정량
| Metric | Baseline | Ours | Δ |
|--------|----------|------|---|
| <metric 1> | | | |
| <metric 2> | | | |

N-fold: mean +/- std 형식

### 정성
<실패 케이스, 시각화, 관찰>

## 6. 해석
- 가설 검증: 지지 / 기각 / 부분 지지
- 원인 분석: <왜 이런 결과가 나왔는가>
- 한계: <이 결과로 주장할 수 없는 것>

## 7. 후속 실험 제안
- <다음에 해볼 것 — 가장 작은 실험 단위로>

## 8. 관련 문서
- [RQ-XXX](../notes/research_questions/RQ-XXX.md)
- [CON-XXX](../notes/concepts/CON-XXX.md)
- [DEC-XXX](../notes/decisions/DEC-XXX.md) (결과 기반 결정이 있을 때)

## 9. 변경 이력
| 날짜 | 내용 |
|------|------|
| <YYYY-MM-DD> | draft |
