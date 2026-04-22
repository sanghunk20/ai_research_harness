Phase의 다음 pending step을 실행하라. 인자가 주어지면 해당 phase를 실행하고, 없으면 전체 phase 상태를 보여주고 어떤 phase를 실행할지 물어봐라.

## 실행 절차

### 1. 인자 확인
- 인자가 있으면 (예: `phase-B`) → 해당 phase 실행
- 인자가 없으면 → `70_projects/phases/index.json`을 읽고 in_progress/pending phase 목록을 보여준 뒤 선택 요청

### 2. Phase index.json 읽기
`70_projects/phases/{phase-dir}/index.json`을 읽고 다음 pending step을 찾아라.

### 3. GPU 점유 확인 (train step인 경우)

```bash
nvidia-smi --query-gpu=index,name,utilization.gpu,memory.used,memory.total --format=csv,noheader
nvidia-smi --query-compute-apps=pid,gpu_uuid,used_memory,name --format=csv,noheader
```

**CRITICAL**: 다른 사용자의 프로세스가 GPU를 점유하고 있으면:
- 점유 중인 GPU의 VRAM 사용량을 보여줘라
- **"다른 프로세스가 GPU를 사용 중입니다. 학습을 시작할까요?"** 라고 반드시 컨펌 받아라
- 컨펌 없이 학습을 시작하지 마라

### 4. Step 유형별 실행

**code step**: 해당 step.md의 지시에 따라 코드 작성/config 생성 수행

**train step**:
1. GPU 확인 (위 3번)
2. **dry-run 먼저 실행 (CRITICAL)**:
   ```bash
   conda run -n landmark_detect python {train_script} --config {config} --dry-run
   ```
   - dry-run 성공 → 본 학습 진행
   - dry-run 실패 (OOM, import error, config 오류 등) → status를 `"blocked"`로 설정, 에러 내용을 `"blocked_reason"`에 기록, 본 학습을 시작하지 마라
   - dry-run에서 training_complete.flag를 생성하지 않도록 주의
3. tmux 세션에서 본 학습 시작:
   ```bash
   tmux new-session -d -s "harness-{phase}-{step}" \
     "sudo -u sanghunk20 bash -c 'conda run -n landmark_detect {training_command}'"
   ```
4. tmux 세션 존재 확인: `tmux has-session -t harness-{phase}-{step}`
5. index.json의 해당 step을 `"status": "training"`, `"tmux_session": "harness-{phase}-{step}"` 으로 업데이트
6. 사용자에게 보고: "dry-run 통과, 학습이 tmux에서 시작됐습니다. `tmux attach -t harness-{phase}-{step}`로 확인 가능합니다."

**eval step**: 해당 step.md의 지시에 따라 평가 실행 (conda run -n landmark_detect ...)

**analyze step**: 결과 파일을 읽고 분석, 비교표 생성, PROJ 문서 업데이트

### 5. Step 완료 후
1. `index.json`의 해당 step status를 `"completed"` + `"summary"` 업데이트
2. 70_projects/phases/index.json의 해당 phase progress 업데이트
3. 다음 pending step이 있으면 계속 진행할지 물어봐라

### 6. step.md 파일이 없는 경우
해당 step의 name과 type을 보고 적절한 작업을 수행하라. step.md가 없어도 index.json의 step 정보만으로 실행 가능해야 한다.
