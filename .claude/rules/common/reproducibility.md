# Reproducibility 규칙 (AI 연구 공통)

논문 리뷰어가 가장 먼저 지적하는 영역입니다. 모든 실험은 **동일 입력 → 동일 출력**이 성립해야 합니다.

## 필수 규칙

### 1. Seed 고정

모든 학습/평가 스크립트는 진입점에서 seed를 고정:

```python
import random, numpy as np, torch
random.seed(seed); np.random.seed(seed)
torch.manual_seed(seed); torch.cuda.manual_seed_all(seed)
```

- Config의 `experiment.seed`를 단일 소스로 사용
- `DataLoader`에 `worker_init_fn`과 `generator`로 seed 전달 (multi-worker 시 필요)
- 완전 결정론이 필요하면 `torch.use_deterministic_algorithms(True)` + `CUBLAS_WORKSPACE_CONFIG=:4096:8` — 속도 손실 있음, 선택 적용

### 2. Env Lock

학습 시작 전 env snapshot을 실험 디렉토리에 저장:

```bash
conda env export --no-builds > experiments/logs/<exp_id>/env.yaml
pip freeze > experiments/logs/<exp_id>/requirements.txt
```

이 파일은 `git add`로 checkpoint와 함께 커밋하지 말고, 실험 디렉토리에만 보관 (checkpoint가 gitignored이므로 같이 묻힘).

### 3. Git Commit Hash 기록

학습 시작 시 현재 commit hash를 로그 메타데이터에 기록:

```python
import subprocess
sha = subprocess.check_output(["git", "rev-parse", "HEAD"]).decode().strip()
dirty = bool(subprocess.check_output(["git", "status", "--porcelain"]).strip())
metadata["git_commit"] = sha + ("-dirty" if dirty else "")
```

`-dirty`면 uncommitted 변경이 있다는 뜻. 가능하면 학습 전 커밋 권장.

### 4. 데이터 Split 고정

- Train/Val/Test split은 **명시적 파일**로 저장 (`data/splits/fold0.json` 등)
- 코드 안에서 `random.split()`으로 매번 분할 금지
- split 파일은 데이터와 함께 `data_backup/`에 원본 보관

### 5. Checkpoint & Data Hash

Eval 재현성 검증용 — eval 스크립트가 다음을 기록:

```python
ckpt_sha = hashlib.sha256(open(ckpt_path, "rb").read()).hexdigest()[:16]
# 데이터셋 split 파일도 동일하게
```

`experiments/eval/<exp_id>/metrics.json`에 `{ckpt_hash, split_hash, git_commit}`를 포함.

### 6. 평가 결과 재현성 테스트

주요 결과는 seed 3~5개로 반복하여 **mean +/- std** 보고. 단일 seed 결과는 논문 주요 표에 쓰지 말 것.

## 권장 사항

### 7. Config Snapshot

학습 시작 시 최종 resolved config를 `experiments/logs/<exp_id>/config.resolved.yaml`로 덤프. CLI override, 환경변수 치환까지 반영된 실제 사용 값.

### 8. Deterministic 여부 명시

논문 methodology 섹션에 "결과는 `torch.use_deterministic_algorithms`를 사용하지 않았다 / 사용했다"를 명시.

### 9. 논문/리포트 체크리스트

결과 보고 전 확인:
- [ ] Seed 값이 config/논문에 명시되어 있는가
- [ ] N-fold / N-seed 결과가 mean +/- std로 보고되는가
- [ ] checkpoint hash 또는 git commit이 기록되어 있는가
- [ ] env.yaml / requirements.txt가 실험 디렉토리에 있는가
- [ ] 데이터 split 파일이 검증 가능한 형태로 공개 가능한가

## 준수 확인

`/harness` 또는 `/train` 실행 시 execute.py의 train step은 위 1~3을 자동으로 수행하도록 학습 스크립트에 구현되어야 합니다. 구현이 빠져 있으면 code step에서 먼저 추가 후 train step으로 넘어갑니다.
