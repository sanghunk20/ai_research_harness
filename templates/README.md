# templates/

`/setup`이 프로젝트 초기화 시 참조하는 템플릿 + Vision 연구에서 재사용 가능한 코드 skeleton.

## 문서 템플릿

| 파일 | 복사 위치 | 용도 |
|------|----------|------|
| `EXP_template.md` | `experiments/logs/EXP-YYYYMMDD-XX.md` | 개별 실험 기록 |
| `REF_template.md` | `notes/references/REF-<Name>.md` | 참고 논문 리뷰 |

## 코드 skeleton

| 파일 | 복사 위치 | 용도 |
|------|----------|------|
| `train_config.yaml` | `src/configs/<exp_name>.yaml` | 학습 config |
| `dataset_base.py` | `src/<pkg>/datasets/base.py` | Vision dataset 공통 베이스 (Sample dataclass + BaseVisionDataset) |
| `trainer_base.py` | `src/<pkg>/trainers/base.py` | Trainer 공통 베이스 (fit/evaluate 루프, AMP, best checkpoint skip) |
| `train_vision.py` | `src/scripts/train.py` | 학습 entrypoint (task.type으로 dispatch) |
| `classification_task.py` | `src/<pkg>/tasks/classification.py` | Classification 구현 예시 — segmentation/landmark/detection 구현 시 참고 |

## 사용 흐름

1. `/setup`으로 프로젝트 초기화
2. `phase-baseline`의 code step에서:
   - `train_config.yaml`을 `src/configs/baseline.yaml`로 복사 후 편집
   - `train_vision.py`를 `src/scripts/train.py`로 복사
   - `dataset_base.py`, `trainer_base.py`를 해당 위치로 복사
   - `classification_task.py`를 참고하여 task 구현 파일 작성
3. Dry-run: `python src/scripts/train.py --config src/configs/baseline.yaml --dry-run`
4. 성공 시 `/harness`로 본 학습 진행

## 설계 원칙

- **최소한만 제공**: 각 task별 완전한 구현은 프로젝트에서 작성. 여기서는 인터페이스만.
- **execute.py와의 계약**:
  - 학습 스크립트는 `--dry-run` 플래그 지원
  - dry-run에서 `training_complete.flag` 생성 금지
  - best checkpoint만 저장 (safety 규칙)
  - 기존 완료 학습은 skip
- **참조 경로**: 실제 스키마는 `docs/phase_schema.md` 참조
