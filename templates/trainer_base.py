"""Vision trainer 공통 베이스.

task-specific trainer는 이 BaseTrainer를 상속하여 compute_loss, evaluate만 구현.
복사 경로: src/<package>/trainers/base.py

safety_constraints 준수:
    - 기존 best checkpoint를 덮어쓰지 않음 (skip 로직 포함)
    - dry_run 모드에서 training_complete.flag를 생성하지 않음
    - best checkpoint만 저장
"""
from __future__ import annotations

import json
import logging
from abc import abstractmethod
from pathlib import Path
from typing import Any, Optional

import torch
from torch.utils.data import DataLoader

logger = logging.getLogger(__name__)


class BaseTrainer:
    """공통 학습 루프.

    서브클래스 구현 필수:
        compute_loss(batch, outputs) -> Tensor
        evaluate(loader) -> dict[str, float]   # metric 이름 → 값

    서브클래스가 override하면 유용한 것:
        forward_step(batch) -> outputs  # 기본: self.model(batch["images"])
        should_save_best(metrics, best_so_far) -> bool
    """

    def __init__(
        self,
        model: torch.nn.Module,
        optimizer: torch.optim.Optimizer,
        scheduler: Optional[Any],
        device: torch.device,
        config: dict,
        save_dir: Path,
    ):
        self.model = model
        self.optimizer = optimizer
        self.scheduler = scheduler
        self.device = device
        self.config = config
        self.save_dir = Path(save_dir)
        self.save_dir.mkdir(parents=True, exist_ok=True)

        self.best_metric: Optional[float] = None
        self.best_epoch: int = -1
        self._dry_run: bool = bool(config.get("dry_run", False))

        precision = config.get("train", {}).get("precision", "fp32")
        self._amp_dtype = {"fp16": torch.float16, "bf16": torch.bfloat16}.get(precision)
        self._scaler = torch.amp.GradScaler("cuda") if precision == "fp16" else None

    # --- subclass 구현 필수 ---

    @abstractmethod
    def compute_loss(self, batch: dict, outputs: Any) -> torch.Tensor:
        raise NotImplementedError

    @abstractmethod
    def evaluate(self, loader: DataLoader) -> dict[str, float]:
        """validation/test loader 평가. metric 이름 → 스칼라 값.

        monitor metric (config.eval.monitor)은 반드시 포함해야 함.
        """
        raise NotImplementedError

    # --- 확장 가능 ---

    def forward_step(self, batch: dict) -> Any:
        return self.model(batch["images"].to(self.device, non_blocking=True))

    def should_save_best(self, metrics: dict[str, float]) -> bool:
        cfg = self.config.get("checkpoint", {})
        metric_name = cfg.get("metric", "val/loss")
        mode = cfg.get("mode", "max")
        current = metrics.get(metric_name)
        if current is None:
            return False
        if self.best_metric is None:
            return True
        return (current > self.best_metric) if mode == "max" else (current < self.best_metric)

    # --- 공통 구현 ---

    def fit(
        self,
        train_loader: DataLoader,
        val_loader: DataLoader,
        num_epochs: int,
    ) -> dict[str, float]:
        """전체 학습 루프. best metric을 반환."""
        if self._check_already_completed():
            return self._load_best_metrics()

        log_every = self.config.get("logging", {}).get("log_every_n_steps", 50)
        val_every = self.config.get("logging", {}).get("val_every_n_epochs", 1)

        for epoch in range(num_epochs):
            self._train_one_epoch(train_loader, epoch, log_every)

            if self.scheduler is not None:
                self.scheduler.step()

            if (epoch + 1) % val_every == 0:
                metrics = self.evaluate(val_loader)
                logger.info("epoch=%d  %s", epoch, metrics)
                if self.should_save_best(metrics):
                    self._save_best(epoch, metrics)

            if self._dry_run:
                logger.info("[dry_run] exit after 1 epoch")
                return {"dry_run": 1.0}

        self._mark_training_complete()
        return self._load_best_metrics()

    def _train_one_epoch(self, loader: DataLoader, epoch: int, log_every: int):
        self.model.train()
        for step, batch in enumerate(loader):
            self.optimizer.zero_grad(set_to_none=True)

            if self._amp_dtype is not None:
                with torch.autocast(device_type=self.device.type, dtype=self._amp_dtype):
                    outputs = self.forward_step(batch)
                    loss = self.compute_loss(batch, outputs)
                if self._scaler is not None:
                    self._scaler.scale(loss).backward()
                    self._scaler.unscale_(self.optimizer)
                    self._clip_grad()
                    self._scaler.step(self.optimizer)
                    self._scaler.update()
                else:
                    loss.backward()
                    self._clip_grad()
                    self.optimizer.step()
            else:
                outputs = self.forward_step(batch)
                loss = self.compute_loss(batch, outputs)
                loss.backward()
                self._clip_grad()
                self.optimizer.step()

            if step % log_every == 0:
                logger.info("epoch=%d  step=%d  loss=%.4f", epoch, step, loss.item())

            if self._dry_run and step >= 2:
                break

    def _clip_grad(self):
        clip = self.config.get("train", {}).get("grad_clip", 0.0)
        if clip > 0:
            torch.nn.utils.clip_grad_norm_(self.model.parameters(), clip)

    # --- checkpoint ---

    def _best_ckpt_path(self) -> Path:
        return self.save_dir / "best_model.pth"

    def _metrics_path(self) -> Path:
        return self.save_dir / "best_metrics.json"

    def _save_best(self, epoch: int, metrics: dict[str, float]):
        cfg = self.config.get("checkpoint", {})
        if self._dry_run:
            return
        path = self._best_ckpt_path()
        if path.exists() and cfg.get("no_overwrite", False):
            logger.warning("best_model.pth already exists; skipping save.")
            return
        torch.save({"model": self.model.state_dict(), "epoch": epoch}, path)
        self._metrics_path().write_text(json.dumps(metrics, indent=2))
        self.best_metric = metrics.get(cfg.get("metric", "val/loss"))
        self.best_epoch = epoch

    def _check_already_completed(self) -> bool:
        """기존 학습이 완료된 경우 skip."""
        flag = self._completion_flag_path()
        if flag and flag.exists() and self._best_ckpt_path().exists():
            logger.info("이미 완료된 학습입니다. skip: %s", self.save_dir)
            return True
        return False

    def _completion_flag_path(self) -> Optional[Path]:
        cfg = self.config.get("checkpoint", {})
        flag_str = cfg.get("completion_flag")
        return Path(flag_str) if flag_str else None

    def _mark_training_complete(self):
        if self._dry_run:
            return
        flag = self._completion_flag_path()
        if flag:
            flag.parent.mkdir(parents=True, exist_ok=True)
            flag.touch()

    def _load_best_metrics(self) -> dict[str, float]:
        p = self._metrics_path()
        if p.exists():
            return json.loads(p.read_text())
        return {}
