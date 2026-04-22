"""Vision 학습 스크립트 엔트리포인트.

복사 경로: src/scripts/train.py

호출 예시 (harness/execute.py의 train step에서):
    conda run -n <CONDA_ENV> python src/scripts/train.py \\
        --config src/configs/<exp>.yaml

Dry-run (code step 마지막에 필수):
    conda run -n <CONDA_ENV> python src/scripts/train.py \\
        --config src/configs/<exp>.yaml --dry-run

설계 원칙:
    - Task-specific한 Dataset/Model/Trainer는 config.task.type으로 분기
    - safety: 기존 best_model.pth 존재 시 skip (BaseTrainer가 처리)
    - dry-run에서 training_complete.flag 생성 안 함
"""
from __future__ import annotations

import argparse
import logging
import random
from pathlib import Path

import numpy as np
import torch
import yaml
from torch.utils.data import DataLoader

# 서브클래스 import — 프로젝트에 맞게 경로 조정
# from mypkg.datasets.classification import ClassificationDataset
# from mypkg.trainers.classification import ClassificationTrainer
# from mypkg.models.builder import build_model

logging.basicConfig(
    format="%(asctime)s  %(levelname)s  %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--config", required=True, type=Path)
    p.add_argument("--dry-run", action="store_true",
                   help="1 epoch, 적은 batch로 sanity check. training_complete.flag 생성 안 함.")
    p.add_argument("--resume-from", type=Path, default=None)
    return p.parse_args()


def load_config(path: Path, dry_run: bool) -> dict:
    cfg = yaml.safe_load(path.read_text())
    if dry_run:
        overrides = cfg.get("dry_run", {})
        cfg["train"]["epochs"] = overrides.get("epochs", 1)
        cfg["train"]["batch_size"] = overrides.get("batch_size", 4)
        cfg["data"]["num_workers"] = overrides.get("num_workers", 0)
        cfg["dry_run"] = True
        if overrides.get("skip_completion_flag", True):
            cfg["checkpoint"]["completion_flag"] = None
    else:
        cfg["dry_run"] = False
    return cfg


def set_seed(seed: int):
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)


def build_task(cfg: dict, device: torch.device):
    """task type에 따라 Dataset/Model/Trainer를 반환.

    프로젝트의 실제 구현에서는 각 task 모듈에서 import.
    여기서는 인터페이스만 보인다.
    """
    task_type = cfg["task"]["type"]
    if task_type == "classification":
        # from mypkg.tasks.classification import build as build_fn
        raise NotImplementedError("src/<pkg>/tasks/classification.py의 build()를 구현해서 연결하세요")
    elif task_type == "segmentation":
        raise NotImplementedError("src/<pkg>/tasks/segmentation.py의 build()를 구현해서 연결하세요")
    elif task_type == "landmark":
        raise NotImplementedError("src/<pkg>/tasks/landmark.py의 build()를 구현해서 연결하세요")
    elif task_type == "detection":
        raise NotImplementedError("src/<pkg>/tasks/detection.py의 build()를 구현해서 연결하세요")
    else:
        raise ValueError(f"Unknown task.type: {task_type}")


def main():
    args = parse_args()
    cfg = load_config(args.config, args.dry_run)
    set_seed(cfg["experiment"]["seed"])

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    logger.info("device=%s  dry_run=%s", device, cfg["dry_run"])

    # Task별 Dataset/Model/Trainer 구성
    train_set, val_set, model, trainer_cls = build_task(cfg, device)

    train_loader = DataLoader(
        train_set,
        batch_size=cfg["train"]["batch_size"],
        shuffle=True,
        num_workers=cfg["data"]["num_workers"],
        pin_memory=True,
    )
    val_loader = DataLoader(
        val_set,
        batch_size=cfg["train"]["batch_size"],
        shuffle=False,
        num_workers=cfg["data"]["num_workers"],
        pin_memory=True,
    )

    optim_cfg = cfg["train"]["optimizer"]
    optimizer = torch.optim.AdamW(
        model.parameters(),
        lr=optim_cfg["lr"],
        weight_decay=optim_cfg["weight_decay"],
        betas=optim_cfg["betas"],
    )

    sched_cfg = cfg["train"].get("scheduler", {})
    scheduler = None
    if sched_cfg.get("name") == "cosine":
        scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(
            optimizer,
            T_max=cfg["train"]["epochs"],
            eta_min=sched_cfg.get("min_lr", 0),
        )

    save_dir = Path(cfg["checkpoint"]["save_dir"])
    trainer = trainer_cls(
        model=model.to(device),
        optimizer=optimizer,
        scheduler=scheduler,
        device=device,
        config=cfg,
        save_dir=save_dir,
    )

    best_metrics = trainer.fit(
        train_loader=train_loader,
        val_loader=val_loader,
        num_epochs=cfg["train"]["epochs"],
    )
    logger.info("best_metrics=%s", best_metrics)


if __name__ == "__main__":
    main()
