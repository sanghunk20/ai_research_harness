#!/usr/bin/env python3
"""
AI Research Harness — Phase/Step Executor

Phase 내 step을 순차 실행하고 자가 교정한다.
학습(train) step은 tmux로 백그라운드 실행하며, 완료 시 자동으로 다음 step을 진행한다.

Usage:
    python harness/execute.py <phase-dir>              # 순차 실행
    python harness/execute.py <phase-dir> --resume     # 학습 완료 후 재개
    python harness/execute.py <phase-dir> --step 2     # 특정 step만 실행
    python harness/execute.py <phase-dir> --dry-run    # 실행 계획만 출력
    python harness/execute.py <phase-dir> --status     # 현재 상태 출력
    python harness/execute.py <phase-dir> --push       # 실행 후 push

Adapted from: https://github.com/jha0313/harness_framework

Configuration:
    Edit the constants below (PHASES_DIR, CONDA_ENV, TRAIN_USER, etc.)
    to match your project setup.
"""

import argparse
import contextlib
import json
import os
import subprocess
import sys
import threading
import time
import types
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional

# ============================================================================
# PROJECT CONFIGURATION — Edit these for your project
# ============================================================================

ROOT = Path(__file__).resolve().parent.parent
PROJECT_ROOT = ROOT

# Phase tracking directory
PHASES_DIR = ROOT / "projects" / "phases"

# Conda environment name
CONDA_ENV = "{CONDA_ENV}"  # e.g., "landmark_detect"

# User to run training as (for shared servers with sudo)
# Set to None if not using sudo/user switching
TRAIN_USER = "{TRAIN_USER}"  # e.g., "sanghunk20", or None

# tmux session name prefix
TMUX_PREFIX = "harness"

# Timezone for timestamps
TZ_OFFSET_HOURS = 9  # KST

# Protected paths — NEVER modified by harness
PROTECTED_PATHS = [
    ROOT / "data_backup",
    ROOT / "data",
]

# ============================================================================


@contextlib.contextmanager
def progress_indicator(label: str):
    """터미널 진행 표시기."""
    frames = "◐◓◑◒"
    stop = threading.Event()
    t0 = time.monotonic()

    def _animate():
        idx = 0
        while not stop.wait(0.12):
            sec = int(time.monotonic() - t0)
            sys.stderr.write(f"\r{frames[idx % len(frames)]} {label} [{sec}s]")
            sys.stderr.flush()
            idx += 1
        sys.stderr.write("\r" + " " * (len(label) + 20) + "\r")
        sys.stderr.flush()

    th = threading.Thread(target=_animate, daemon=True)
    th.start()
    info = types.SimpleNamespace(elapsed=0.0)
    try:
        yield info
    finally:
        stop.set()
        th.join()
        info.elapsed = time.monotonic() - t0


def validate_path_safety(path: Path) -> bool:
    """경로가 프로젝트 내부인지, 보호 경로가 아닌지 확인."""
    try:
        resolved = path.resolve()
        if not resolved.is_relative_to(PROJECT_ROOT.resolve()):
            return False
        for protected in PROTECTED_PATHS:
            if resolved.is_relative_to(protected.resolve()):
                return False
        return True
    except (ValueError, OSError):
        return False


def check_gpu() -> dict:
    """GPU 가용성, 개수, 다른 프로세스 점유 현황 확인.

    공유 서버이므로 다른 사용자의 GPU 점유 상태를 반드시 확인한다.
    """
    try:
        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=index,name,memory.total,memory.free,utilization.gpu",
             "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=10,
        )
        if result.returncode != 0:
            return {"available": False, "count": 0, "gpus": [], "processes": [],
                    "error": result.stderr.strip()}

        gpus = []
        for line in result.stdout.strip().split("\n"):
            if not line.strip():
                continue
            parts = [p.strip() for p in line.split(",")]
            if len(parts) >= 5:
                total = int(parts[2])
                free = int(parts[3])
                gpus.append({
                    "index": int(parts[0]),
                    "name": parts[1],
                    "memory_total_mb": total,
                    "memory_free_mb": free,
                    "memory_used_mb": total - free,
                    "utilization_pct": int(parts[4]),
                })

        # GPU 프로세스 확인 (다른 사용자 점유 감지)
        proc_result = subprocess.run(
            ["nvidia-smi", "--query-compute-apps=pid,gpu_bus_id,used_memory,process_name",
             "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=10,
        )
        processes = []
        other_user_using = False
        if proc_result.returncode == 0 and proc_result.stdout.strip():
            for line in proc_result.stdout.strip().split("\n"):
                if not line.strip():
                    continue
                parts = [p.strip() for p in line.split(",")]
                if len(parts) >= 4:
                    pid = int(parts[0])
                    proc_info = {
                        "pid": pid,
                        "gpu_bus_id": parts[1],
                        "used_memory_mb": int(parts[2]) if parts[2].isdigit() else 0,
                        "process_name": parts[3],
                    }
                    try:
                        owner_result = subprocess.run(
                            ["ps", "-o", "user=", "-p", str(pid)],
                            capture_output=True, text=True, timeout=5,
                        )
                        proc_info["owner"] = owner_result.stdout.strip()
                        if TRAIN_USER and proc_info["owner"] and proc_info["owner"] != TRAIN_USER:
                            other_user_using = True
                    except Exception:
                        proc_info["owner"] = "unknown"
                    processes.append(proc_info)

        return {
            "available": len(gpus) > 0,
            "count": len(gpus),
            "gpus": gpus,
            "processes": processes,
            "other_user_using": other_user_using,
        }
    except FileNotFoundError:
        return {"available": False, "count": 0, "gpus": [], "processes": [],
                "error": "nvidia-smi not found"}
    except Exception as e:
        return {"available": False, "count": 0, "gpus": [], "processes": [],
                "error": str(e)}


def tmux_session_exists(session_name: str) -> bool:
    """tmux 세션 존재 여부 확인."""
    if not session_name:
        return False
    try:
        r = subprocess.run(
            ["tmux", "has-session", "-t", session_name],
            capture_output=True, text=True, timeout=10,
        )
        return r.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def get_tmux_sessions(prefix: str = TMUX_PREFIX) -> list:
    """하네스 관련 tmux 세션 목록."""
    try:
        r = subprocess.run(
            ["tmux", "list-sessions", "-F", "#{session_name}:#{session_activity}"],
            capture_output=True, text=True, timeout=10,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return []
    if r.returncode != 0:
        return []
    sessions = []
    for line in r.stdout.strip().split("\n"):
        if line.startswith(prefix):
            sessions.append(line.split(":")[0])
    return sessions


def _build_train_command(cmd: str) -> str:
    """학습 명령어를 TRAIN_USER와 CONDA_ENV로 래핑."""
    inner = f"conda run -n {CONDA_ENV} {cmd}"
    if TRAIN_USER:
        return f"sudo -u {TRAIN_USER} bash -c '{inner}'"
    return inner


class StepExecutor:
    """Phase 디렉토리 안의 step들을 순차 실행하는 하네스."""

    MAX_RETRIES = 3
    FEAT_MSG = "feat({phase}): step {num} — {name}"
    CHORE_MSG = "chore({phase}): step {num} output"
    TZ = timezone(timedelta(hours=TZ_OFFSET_HOURS))

    # Train step polling
    TRAIN_POLL_INTERVAL = 60   # seconds between completion checks
    TRAIN_MAX_POLL = 86400     # max 24h polling

    def __init__(self, phase_dir_name: str, *, auto_push: bool = False,
                 resume: bool = False, only_step: Optional[int] = None,
                 dry_run: bool = False, show_status: bool = False):
        self._phases_dir = PHASES_DIR
        self._phase_dir = self._phases_dir / phase_dir_name
        self._phase_dir_name = phase_dir_name
        self._top_index_file = self._phases_dir / "index.json"
        self._auto_push = auto_push
        self._resume = resume
        self._only_step = only_step
        self._dry_run = dry_run
        self._show_status = show_status

        if not self._phase_dir.is_dir():
            print(f"ERROR: {self._phase_dir} not found")
            sys.exit(1)

        self._index_file = self._phase_dir / "index.json"
        if not self._index_file.exists():
            print(f"ERROR: {self._index_file} not found")
            sys.exit(1)

        try:
            idx = self._read_json(self._index_file)
        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            print(f"ERROR: {self._index_file} 파싱 실패: {e}")
            sys.exit(1)

        if "steps" not in idx or not isinstance(idx["steps"], list):
            print(f"ERROR: {self._index_file}에 'steps' 배열이 없습니다.")
            sys.exit(1)

        self._project = idx.get("project", "project")
        self._phase_name = idx.get("phase", phase_dir_name)
        self._total = len(idx["steps"])

        # Compute relative path from ROOT to phases dir for commit messages
        try:
            self._phases_rel = self._phases_dir.relative_to(ROOT)
        except ValueError:
            self._phases_rel = Path("projects/phases")

    def run(self):
        if self._show_status:
            self._print_status()
            return
        if self._dry_run:
            self._print_dry_run()
            return

        self._print_header()
        self._check_blockers()
        self._checkout_branch()
        guardrails = self._load_guardrails()
        self._ensure_created_at()

        if self._only_step is not None:
            self._execute_single_step_by_num(self._only_step, guardrails)
        else:
            self._execute_all_steps(guardrails)
            self._finalize()

    # --- timestamps ---

    def _stamp(self) -> str:
        return datetime.now(self.TZ).strftime("%Y-%m-%dT%H:%M:%S%z")

    # --- JSON I/O ---

    @staticmethod
    def _read_json(p: Path) -> dict:
        return json.loads(p.read_text(encoding="utf-8"))

    @staticmethod
    def _write_json(p: Path, data: dict):
        p.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

    # --- git ---

    def _run_git(self, *args) -> subprocess.CompletedProcess:
        cmd = ["git"] + list(args)
        return subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True)

    def _checkout_branch(self):
        branch = f"feat-{self._phase_name}"

        r = self._run_git("rev-parse", "--abbrev-ref", "HEAD")
        if r.returncode != 0:
            print(f"  ERROR: git을 사용할 수 없거나 git repo가 아닙니다.")
            print(f"  {r.stderr.strip()}")
            sys.exit(1)

        if r.stdout.strip() == branch:
            return

        r = self._run_git("rev-parse", "--verify", branch)
        r = (self._run_git("checkout", branch) if r.returncode == 0
             else self._run_git("checkout", "-b", branch))

        if r.returncode != 0:
            print(f"  ERROR: 브랜치 '{branch}' checkout 실패.")
            print(f"  {r.stderr.strip()}")
            print(f"  Hint: 변경사항을 stash하거나 commit한 후 다시 시도하세요.")
            sys.exit(1)

        print(f"  Branch: {branch}")

    def _commit_step(self, step_num: int, step_name: str):
        output_rel = str(self._phases_rel / self._phase_dir_name / f"step{step_num}-output.json")
        index_rel = str(self._phases_rel / self._phase_dir_name / "index.json")

        self._run_git("add", "-A")
        self._run_git("reset", "HEAD", "--", output_rel)
        self._run_git("reset", "HEAD", "--", index_rel)

        if self._run_git("diff", "--cached", "--quiet").returncode != 0:
            msg = self.FEAT_MSG.format(phase=self._phase_name, num=step_num, name=step_name)
            r = self._run_git("commit", "-m", msg)
            if r.returncode == 0:
                print(f"  Commit: {msg}")
            else:
                print(f"  WARN: 코드 커밋 실패: {r.stderr.strip()}")

        self._run_git("add", "-A")
        if self._run_git("diff", "--cached", "--quiet").returncode != 0:
            msg = self.CHORE_MSG.format(phase=self._phase_name, num=step_num)
            r = self._run_git("commit", "-m", msg)
            if r.returncode != 0:
                print(f"  WARN: housekeeping 커밋 실패: {r.stderr.strip()}")

    # --- top-level index ---

    def _update_top_index(self, status: str):
        if not self._top_index_file.exists():
            return
        top = self._read_json(self._top_index_file)
        ts = self._stamp()
        for phase in top.get("phases", []):
            if phase.get("dir") == self._phase_dir_name:
                phase["status"] = status
                ts_key = {
                    "completed": "completed_at",
                    "error": "failed_at",
                    "blocked": "blocked_at",
                }.get(status)
                if ts_key:
                    phase[ts_key] = ts
                break
        self._write_json(self._top_index_file, top)

    # --- guardrails & context ---

    def _load_guardrails(self) -> str:
        sections = []

        claude_md = ROOT / "CLAUDE.md"
        if claude_md.exists():
            sections.append(f"## 프로젝트 규칙 (CLAUDE.md)\n\n{claude_md.read_text()}")

        agents_md = ROOT / "AGENTS.md"
        if agents_md.exists():
            sections.append(f"## 에이전트 가이드 (AGENTS.md)\n\n{agents_md.read_text()}")

        rules_dir = ROOT / ".claude" / "rules"
        if rules_dir.is_dir():
            for subdir in sorted(rules_dir.iterdir()):
                if subdir.is_dir():
                    for doc in sorted(subdir.glob("*.md")):
                        sections.append(f"## Rule: {doc.stem}\n\n{doc.read_text()}")
                elif subdir.suffix == ".md":
                    sections.append(f"## Rule: {subdir.stem}\n\n{subdir.read_text()}")

        return "\n\n---\n\n".join(sections) if sections else ""

    @staticmethod
    def _build_step_context(index: dict) -> str:
        lines = [
            f"- Step {s['step']} ({s['name']}): {s['summary']}"
            for s in index["steps"]
            if s["status"] == "completed" and s.get("summary")
        ]
        if not lines:
            return ""
        return "## 이전 Step 산출물\n\n" + "\n".join(lines) + "\n\n"

    def _build_preamble(self, guardrails: str, step_context: str,
                        step: dict, prev_error: Optional[str] = None) -> str:
        commit_example = self.FEAT_MSG.format(
            phase=self._phase_name, num="N", name="<step-name>"
        )
        retry_section = ""
        if prev_error:
            retry_section = (
                f"\n## 이전 시도 실패 — 아래 에러를 반드시 참고하여 수정하라\n\n"
                f"{prev_error}\n\n---\n\n"
            )

        step_type = step.get("type", "code")
        type_instructions = self._get_type_instructions(step_type)

        safety_rules = (
            f"\n## 안전 규칙 (CRITICAL)\n\n"
            f"1. 모든 파일 생성/수정/삭제는 반드시 {PROJECT_ROOT} 내부에서만 수행하라.\n"
            f"2. rm -rf 명령어는 절대 사용하지 마라.\n"
            f"3. / 바로 하위 경로(예: /root, /home, /etc)를 직접 수정하지 마라.\n"
            f"4. data_backup/ 디렉토리는 절대 수정하지 마라.\n"
            f"5. 파일 삭제가 필요하면 삭제 대상 목록을 출력하고 중단하라 (status: blocked).\n\n"
        )

        phases_rel = str(self._phases_rel)
        return (
            f"당신은 {self._project} 프로젝트의 AI 연구 협력자입니다. 아래 step을 수행하세요.\n\n"
            f"{guardrails}\n\n---\n\n"
            f"{step_context}{retry_section}"
            f"{type_instructions}"
            f"{safety_rules}"
            f"## 작업 규칙\n\n"
            f"1. 이전 step에서 작성된 코드를 확인하고 일관성을 유지하라.\n"
            f"2. 이 step에 명시된 작업만 수행하라. 추가 기능이나 파일을 만들지 마라.\n"
            f"3. AC(Acceptance Criteria) 검증을 직접 실행하라.\n"
            f"4. /{phases_rel}/{self._phase_dir_name}/index.json의 해당 step status를 업데이트하라:\n"
            f"   - AC 통과 → \"completed\" + \"summary\" 필드에 이 step의 산출물을 한 줄로 요약\n"
            f"   - {self.MAX_RETRIES}회 수정 시도 후에도 실패 → \"error\" + \"error_message\" 기록\n"
            f"   - 사용자 개입이 필요한 경우 → \"blocked\" + \"blocked_reason\" 기록 후 즉시 중단\n"
            f"5. 모든 변경사항을 커밋하라:\n"
            f"   {commit_example}\n\n---\n\n"
        )

    @staticmethod
    def _get_type_instructions(step_type: str) -> str:
        """Step 유형별 추가 지시사항."""
        if step_type == "train":
            gpu_info = json.dumps(check_gpu(), ensure_ascii=False, indent=2)
            train_cmd_example = (
                f"sudo -u {TRAIN_USER} bash -c 'conda run -n {CONDA_ENV} <cmd>'"
                if TRAIN_USER
                else f"conda run -n {CONDA_ENV} <cmd>"
            )
            return (
                f"## Step 유형: train (모델 학습)\n\n"
                f"### GPU 상태 (공유 서버)\n```json\n{gpu_info}\n```\n\n"
                f"### GPU 점유 확인 (CRITICAL)\n"
                f"위 GPU 상태에서 `other_user_using`이 true이거나, `processes`에 다른 사용자의 "
                f"프로세스가 있으면:\n"
                f"1. 점유 중인 GPU 번호, VRAM 사용량, 프로세스 소유자를 표시하라.\n"
                f"2. **반드시 사용자에게 \"다른 프로세스가 GPU를 사용 중입니다. 학습을 시작할까요?\"**\n"
                f"   라고 컨펌을 요청하라.\n"
                f"3. 컨펌 없이 학습을 시작하지 마라. → status를 \"blocked\"로 설정하고 이유를 기록하라.\n\n"
                f"### 학습 실행 규칙\n"
                f"1. GPU가 충분한지 확인하라 (DDP 필요 시 2개 이상).\n"
                f"2. 학습은 반드시 tmux 세션 안에서 실행하라:\n"
                f"   ```bash\n"
                f"   tmux new-session -d -s \"{TMUX_PREFIX}-<phase>-<step>\" \\\n"
                f"     \"{train_cmd_example}\"\n"
                f"   ```\n"
                f"3. 학습 시작 후 tmux 세션이 존재하는지 확인하라 (tmux has-session -t ...).\n"
                f"4. checkpoint 저장 경로와 training_complete.flag 위치를 summary에 기록하라.\n"
                f"5. 학습 시작이 확인되면 status를 \"training\"으로 설정하라.\n\n"
            )
        elif step_type == "eval":
            return (
                f"## Step 유형: eval (모델 평가)\n\n"
                f"### 평가 규칙\n"
                f"1. conda 환경: {CONDA_ENV}\n"
                f"2. 결과를 mean +/- std 형식으로 정리하라.\n"
                f"3. 시각화 이미지는 평가 시에만 생성.\n\n"
            )
        elif step_type == "analyze":
            return (
                f"## Step 유형: analyze (결과 분석)\n\n"
                f"### 분석 규칙\n"
                f"1. 결과 파일을 직접 읽고 분석하라.\n"
                f"2. N-fold 결과는 mean +/- std로 보고하라.\n"
                f"3. 프로젝트 문서를 업데이트하라.\n\n"
            )
        else:  # code
            return (
                f"## Step 유형: code (코드 작성)\n\n"
                f"### 코드 작성 규칙\n"
                f"1. conda 환경: {CONDA_ENV}\n"
                f"2. 기존 코드와의 일관성을 유지하라.\n"
                f"3. 학습 스크립트에는 완료된 학습 skip 로직을 포함하라.\n"
                f"4. dry-run 모드에서는 training_complete.flag를 생성하지 마라.\n"
                f"5. checkpoint는 best만 저장하라.\n\n"
            )

    # --- Claude 호출 ---

    def _invoke_claude(self, step: dict, preamble: str) -> dict:
        step_num, step_name = step["step"], step["name"]
        step_file = self._phase_dir / f"step{step_num}.md"

        if not step_file.exists():
            print(f"  ERROR: {step_file} not found")
            sys.exit(1)

        prompt = preamble + step_file.read_text()
        try:
            result = subprocess.run(
                ["claude", "-p", "--dangerously-skip-permissions",
                 "--output-format", "json", prompt],
                cwd=str(ROOT), capture_output=True, text=True, timeout=3600,
            )
        except subprocess.TimeoutExpired:
            print(f"\n  ERROR: Claude 실행 시간 초과 (60분)")
            result = types.SimpleNamespace(
                returncode=1, stdout="", stderr="TimeoutExpired after 3600s"
            )
        except FileNotFoundError:
            print(f"\n  ERROR: claude CLI를 찾을 수 없습니다. PATH를 확인하세요.")
            sys.exit(1)

        if result.returncode != 0:
            print(f"\n  WARN: Claude가 비정상 종료됨 (code {result.returncode})")
            if result.stderr:
                print(f"  stderr: {result.stderr[:500]}")

        output = {
            "step": step_num, "name": step_name,
            "exitCode": result.returncode,
            "stdout": result.stdout, "stderr": result.stderr,
        }
        out_path = self._phase_dir / f"step{step_num}-output.json"
        with open(out_path, "w") as f:
            json.dump(output, f, indent=2, ensure_ascii=False)

        return output

    # --- 헤더 & 검증 ---

    def _print_header(self):
        print(f"\n{'='*60}")
        print(f"  AI Research Harness — Step Executor")
        print(f"  Phase: {self._phase_name} | Steps: {self._total}")
        if self._auto_push:
            print(f"  Auto-push: enabled")
        if self._resume:
            print(f"  Mode: resume (training 완료 확인 후 재개)")
        print(f"{'='*60}")

    def _print_status(self):
        """현재 phase 상태 출력."""
        index = self._read_json(self._index_file)
        print(f"\n  Phase: {self._phase_name}")
        print(f"  {'─'*50}")
        for s in index["steps"]:
            icon = {
                "completed": "[done]", "pending": "[    ]",
                "error": "[FAIL]", "blocked": "[WAIT]",
                "training": "[ .. ]", "in_progress": "[ .. ]",
            }.get(s["status"], "[????]")
            step_type = s.get("type", "code")
            summary = s.get("summary", "")
            line = f"  {icon} Step {s['step']}: {s['name']} [{step_type}]"
            if summary:
                line += f" — {summary}"
            print(line)

        sessions = get_tmux_sessions()
        if sessions:
            print(f"\n  Active tmux sessions:")
            for sess in sessions:
                print(f"    - {sess}")
        print()

    def _print_dry_run(self):
        """실행 계획만 출력."""
        index = self._read_json(self._index_file)
        print(f"\n  [DRY RUN] Phase: {self._phase_name}")
        print(f"  {'─'*50}")
        for s in index["steps"]:
            step_type = s.get("type", "code")
            status = s["status"]
            step_file = self._phase_dir / f"step{s['step']}.md"
            exists = "OK" if step_file.exists() else "MISSING"
            print(f"  Step {s['step']}: {s['name']} [{step_type}] — {status} — file: {exists}")

        if self._only_step is not None:
            print(f"\n  Only step {self._only_step} will be executed.")

        gpu = check_gpu()
        train_steps = [s for s in index["steps"] if s.get("type") == "train" and s["status"] == "pending"]
        if train_steps:
            print(f"\n  GPU available: {gpu['available']} ({gpu['count']} GPUs)")
            if not gpu["available"]:
                print(f"  WARNING: train step이 있지만 GPU를 사용할 수 없습니다.")
        print()

    def _check_blockers(self):
        index = self._read_json(self._index_file)

        if self._resume:
            for s in index["steps"]:
                if s["status"] == "training":
                    session_name = s.get("tmux_session", "")
                    if session_name and tmux_session_exists(session_name):
                        print(f"\n  Step {s['step']} ({s['name']}) 학습 진행 중.")
                        print(f"    tmux session: {session_name}")
                        print(f"    확인: tmux attach -t {session_name}")
                        sys.exit(0)
                    else:
                        completion_path = s.get("completion_check", "")
                        if completion_path and Path(completion_path).exists():
                            s["status"] = "completed"
                            s["completed_at"] = self._stamp()
                            s["summary"] = s.get("summary", "") + " (학습 완료 확인)"
                            self._write_json(self._index_file, index)
                            print(f"  Step {s['step']} ({s['name']}) 학습 완료 확인!")
                        else:
                            print(f"\n  Step {s['step']} ({s['name']}): tmux 세션 종료됨.")
                            print(f"    completion flag를 확인하세요: {completion_path}")
                            s["status"] = "pending"
                            self._write_json(self._index_file, index)
            return

        for s in index["steps"]:
            if s["status"] == "error":
                print(f"\n  Step {s['step']} ({s['name']}) failed.")
                print(f"  Error: {s.get('error_message', 'unknown')}")
                print(f"  Fix and reset status to 'pending' to retry.")
                sys.exit(1)
            if s["status"] == "blocked":
                print(f"\n  Step {s['step']} ({s['name']}) blocked.")
                print(f"  Reason: {s.get('blocked_reason', 'unknown')}")
                print(f"  Resolve and reset status to 'pending' to retry.")
                sys.exit(2)
            if s["status"] == "training":
                session_name = s.get("tmux_session", "")
                if session_name and tmux_session_exists(session_name):
                    print(f"\n  Step {s['step']} ({s['name']}) 학습 진행 중.")
                    print(f"  tmux session: {session_name}")
                    print(f"  학습 완료 후: python harness/execute.py {self._phase_dir_name} --resume")
                    sys.exit(0)
                else:
                    print(f"  Step {s['step']}: tmux 세션 종료됨, completion 확인 후 재개합니다.")
                    s["status"] = "pending"
                    self._write_json(self._index_file, index)

    def _ensure_created_at(self):
        index = self._read_json(self._index_file)
        if "created_at" not in index:
            index["created_at"] = self._stamp()
            self._write_json(self._index_file, index)

    # --- 실행 루프 ---

    def _execute_single_step_by_num(self, step_num: int, guardrails: str):
        index = self._read_json(self._index_file)
        step = next((s for s in index["steps"] if s["step"] == step_num), None)
        if step is None:
            print(f"  ERROR: Step {step_num} not found")
            sys.exit(1)
        if step["status"] == "completed":
            print(f"  Step {step_num} ({step['name']}) is already completed. Skipping.")
            return
        self._execute_single_step(step, guardrails)

    def _execute_single_step(self, step: dict, guardrails: str) -> bool:
        step_num, step_name = step["step"], step["name"]
        step_type = step.get("type", "code")
        done = sum(1 for s in self._read_json(self._index_file)["steps"]
                    if s["status"] == "completed")
        prev_error = None

        for attempt in range(1, self.MAX_RETRIES + 1):
            index = self._read_json(self._index_file)
            step_context = self._build_step_context(index)
            current_step = next(s for s in index["steps"] if s["step"] == step_num)
            preamble = self._build_preamble(guardrails, step_context, current_step, prev_error)

            tag = f"Step {step_num}/{self._total} ({done} done): {step_name} [{step_type}]"
            if attempt > 1:
                tag += f" [retry {attempt}/{self.MAX_RETRIES}]"

            with progress_indicator(tag) as pi:
                self._invoke_claude(step, preamble)
                elapsed = int(pi.elapsed)

            index = self._read_json(self._index_file)
            status = next(
                (s.get("status", "pending") for s in index["steps"] if s["step"] == step_num),
                "pending"
            )
            ts = self._stamp()

            if status == "completed":
                for s in index["steps"]:
                    if s["step"] == step_num:
                        s["completed_at"] = ts
                self._write_json(self._index_file, index)
                self._commit_step(step_num, step_name)
                print(f"  Step {step_num}: {step_name} completed [{elapsed}s]")
                return True

            if status == "training":
                for s in index["steps"]:
                    if s["step"] == step_num:
                        s["training_started_at"] = ts
                self._write_json(self._index_file, index)
                self._commit_step(step_num, step_name)
                session_name = next(
                    (s.get("tmux_session", "") for s in index["steps"] if s["step"] == step_num),
                    ""
                )
                print(f"  Step {step_num}: {step_name} — 학습 시작됨 [{elapsed}s]")
                print(f"     tmux session: {session_name}")
                print(f"     확인: tmux attach -t {session_name}")

                if self._poll_training_completion(step_num):
                    return True
                else:
                    print(f"     학습 완료 후: python harness/execute.py {self._phase_dir_name} --resume")
                    return False

            if status == "blocked":
                for s in index["steps"]:
                    if s["step"] == step_num:
                        s["blocked_at"] = ts
                self._write_json(self._index_file, index)
                reason = next(
                    (s.get("blocked_reason", "") for s in index["steps"] if s["step"] == step_num),
                    ""
                )
                print(f"  Step {step_num}: {step_name} blocked [{elapsed}s]")
                print(f"    Reason: {reason}")
                self._update_top_index("blocked")
                sys.exit(2)

            err_msg = next(
                (s.get("error_message", "Step did not update status")
                 for s in index["steps"] if s["step"] == step_num),
                "Step did not update status",
            )

            if attempt < self.MAX_RETRIES:
                for s in index["steps"]:
                    if s["step"] == step_num:
                        s["status"] = "pending"
                        s.pop("error_message", None)
                self._write_json(self._index_file, index)
                prev_error = err_msg
                print(f"  Step {step_num}: retry {attempt}/{self.MAX_RETRIES} — {err_msg}")
            else:
                for s in index["steps"]:
                    if s["step"] == step_num:
                        s["status"] = "error"
                        s["error_message"] = f"[{self.MAX_RETRIES} retries failed] {err_msg}"
                        s["failed_at"] = ts
                self._write_json(self._index_file, index)
                self._commit_step(step_num, step_name)
                print(f"  Step {step_num}: {step_name} FAILED after {self.MAX_RETRIES} attempts [{elapsed}s]")
                print(f"    Error: {err_msg}")
                self._update_top_index("error")
                sys.exit(1)

        return False

    def _poll_training_completion(self, step_num: int) -> bool:
        index = self._read_json(self._index_file)
        step = next(s for s in index["steps"] if s["step"] == step_num)
        session_name = step.get("tmux_session", "")
        completion_check = step.get("completion_check", "")

        if not session_name:
            return False

        print(f"\n  Training monitor started (Ctrl+C to detach, --resume to reattach)")

        elapsed = 0
        try:
            while elapsed < self.TRAIN_MAX_POLL:
                time.sleep(self.TRAIN_POLL_INTERVAL)
                elapsed += self.TRAIN_POLL_INTERVAL

                if not tmux_session_exists(session_name):
                    if completion_check and Path(completion_check).exists():
                        index = self._read_json(self._index_file)
                        for s in index["steps"]:
                            if s["step"] == step_num:
                                s["status"] = "completed"
                                s["completed_at"] = self._stamp()
                        self._write_json(self._index_file, index)
                        print(f"\n  Step {step_num}: training completed!")
                        return True
                    else:
                        print(f"\n  tmux session ended, completion flag not found.")
                        print(f"    expected: {completion_check}")
                        return False

                mins = elapsed // 60
                sys.stderr.write(f"\r  Training in progress... ({mins}min elapsed)")
                sys.stderr.flush()

        except KeyboardInterrupt:
            print(f"\n\n  Monitor detached. Training continues in tmux.")
            print(f"    Resume: python harness/execute.py {self._phase_dir_name} --resume")
            return False

        return False

    def _execute_all_steps(self, guardrails: str):
        while True:
            index = self._read_json(self._index_file)
            pending = next((s for s in index["steps"] if s["status"] == "pending"), None)
            if pending is None:
                training = next((s for s in index["steps"] if s["status"] == "training"), None)
                if training:
                    session_name = training.get("tmux_session", "")
                    print(f"\n  Step {training['step']} ({training['name']}) training in progress.")
                    print(f"    Resume after: python harness/execute.py {self._phase_dir_name} --resume")
                    return
                print("\n  All steps completed!")
                return

            step_num = pending["step"]
            for s in index["steps"]:
                if s["step"] == step_num and "started_at" not in s:
                    s["started_at"] = self._stamp()
                    self._write_json(self._index_file, index)
                    break

            if not self._execute_single_step(pending, guardrails):
                return

    def _finalize(self):
        index = self._read_json(self._index_file)

        all_done = all(s["status"] == "completed" for s in index["steps"])
        if not all_done:
            return

        index["completed_at"] = self._stamp()
        self._write_json(self._index_file, index)
        self._update_top_index("completed")

        self._run_git("add", "-A")
        if self._run_git("diff", "--cached", "--quiet").returncode != 0:
            msg = f"chore({self._phase_name}): mark phase completed"
            r = self._run_git("commit", "-m", msg)
            if r.returncode == 0:
                print(f"  {msg}")

        if self._auto_push:
            branch = f"feat-{self._phase_name}"
            r = self._run_git("push", "-u", "origin", branch)
            if r.returncode != 0:
                print(f"\n  ERROR: git push failed: {r.stderr.strip()}")
                sys.exit(1)
            print(f"  Pushed to origin/{branch}")

        print(f"\n{'='*60}")
        print(f"  Phase '{self._phase_name}' completed!")
        print(f"{'='*60}")


def status_all():
    """모든 phase의 상태를 출력."""
    top_index_file = PHASES_DIR / "index.json"
    if not top_index_file.exists():
        print("ERROR: phases/index.json not found")
        sys.exit(1)

    top = json.loads(top_index_file.read_text())
    print(f"\n  {'='*60}")
    print(f"  AI Research Harness — Phase Status")
    print(f"  {'='*60}\n")

    for phase in top.get("phases", []):
        icon = {
            "completed": "[done]", "pending": "[    ]",
            "error": "[FAIL]", "blocked": "[WAIT]",
            "in_progress": "[ .. ]",
        }.get(phase["status"], "[????]")
        progress = phase.get("progress", "")
        progress_str = f" ({progress})" if progress else ""
        print(f"  {icon} {phase['dir']}: {phase.get('name', '')}{progress_str}")

    sessions = get_tmux_sessions()
    if sessions:
        print(f"\n  Active training sessions:")
        for sess in sessions:
            print(f"    [ .. ] {sess}")
    print()


def main():
    parser = argparse.ArgumentParser(
        description="AI Research Harness — Phase/Step Executor",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python harness/execute.py phase-exp1              # Phase 순차 실행
  python harness/execute.py phase-exp1 --resume     # 학습 완료 후 재개
  python harness/execute.py phase-exp1 --step 3     # Step 3만 실행
  python harness/execute.py phase-exp1 --dry-run    # 실행 계획 확인
  python harness/execute.py phase-exp1 --status     # 현재 상태 확인
  python harness/execute.py --status-all            # 모든 phase 상태
        """,
    )
    parser.add_argument("phase_dir", nargs="?", help="Phase directory name (e.g. phase-exp1)")
    parser.add_argument("--push", action="store_true", help="Push branch after completion")
    parser.add_argument("--resume", action="store_true", help="Resume after training completion")
    parser.add_argument("--step", type=int, default=None, help="Execute specific step only")
    parser.add_argument("--dry-run", action="store_true", help="Show execution plan only")
    parser.add_argument("--status", action="store_true", help="Show phase status")
    parser.add_argument("--status-all", action="store_true", help="Show all phases status")
    args = parser.parse_args()

    if args.status_all:
        status_all()
        return

    if not args.phase_dir:
        parser.print_help()
        sys.exit(1)

    executor = StepExecutor(
        args.phase_dir,
        auto_push=args.push,
        resume=args.resume,
        only_step=args.step,
        dry_run=args.dry_run,
        show_status=args.status,
    )
    executor.run()


if __name__ == "__main__":
    main()
