"""Classification task 예시 구현.

복사 경로: src/<package>/tasks/classification.py

Classification은 가장 단순한 케이스로, 다른 task(segmentation/landmark/detection)
구현 시 참고할 수 있는 레퍼런스입니다.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import torch
from torch.utils.data import DataLoader

from .dataset_base import BaseVisionDataset
from .trainer_base import BaseTrainer


class ClassificationDataset(BaseVisionDataset):
    """ImageFolder 스타일. 서브디렉토리 이름이 class."""

    def _list_samples(self):
        records = []
        if self.split_file:
            import json
            split_records = json.loads(self.split_file.read_text())
            # split_file 형식: [{"id": "...", "image_path": "...", "label": N}, ...]
            return [r for r in split_records if r.get("split") == self.split]

        class_dirs = sorted([d for d in self.root.iterdir() if d.is_dir()])
        self.class_to_idx = {d.name: i for i, d in enumerate(class_dirs)}
        for class_dir in class_dirs:
            for img_path in sorted(class_dir.glob("*.jpg")) + sorted(class_dir.glob("*.png")):
                records.append({
                    "id": img_path.stem,
                    "image_path": str(img_path),
                    "label": self.class_to_idx[class_dir.name],
                })
        return records

    def _load_target(self, record: dict) -> int:
        return int(record["label"])


class ClassificationTrainer(BaseTrainer):
    """Cross-entropy 기반 classification trainer."""

    def compute_loss(self, batch: dict, outputs: torch.Tensor) -> torch.Tensor:
        targets = torch.tensor(batch["targets"], device=outputs.device, dtype=torch.long)
        loss_cfg = self.config.get("train", {}).get("loss", {})
        smoothing = loss_cfg.get("label_smoothing", 0.0)
        return torch.nn.functional.cross_entropy(
            outputs, targets, label_smoothing=smoothing,
        )

    def evaluate(self, loader: DataLoader) -> dict[str, float]:
        self.model.eval()
        total, correct1, correct5 = 0, 0, 0
        total_loss = 0.0
        with torch.no_grad():
            for batch in loader:
                outputs = self.forward_step(batch)
                targets = torch.tensor(batch["targets"], device=outputs.device, dtype=torch.long)

                total_loss += torch.nn.functional.cross_entropy(outputs, targets, reduction="sum").item()
                _, top5 = outputs.topk(5, dim=1)
                correct1 += (top5[:, 0] == targets).sum().item()
                correct5 += (top5 == targets.unsqueeze(1)).any(dim=1).sum().item()
                total += targets.numel()

        return {
            "val/loss": total_loss / max(total, 1),
            "val/top1_acc": correct1 / max(total, 1),
            "val/top5_acc": correct5 / max(total, 1),
        }


def build(cfg: dict, device: torch.device):
    """train_vision.py::build_task()가 호출.
    반환: (train_set, val_set, model, trainer_cls)
    """
    # --- model ---
    import torchvision
    backbone_name = cfg["model"]["backbone"]
    pretrained = cfg["model"]["pretrained"] == "imagenet"
    model = getattr(torchvision.models, backbone_name)(
        weights="IMAGENET1K_V2" if pretrained else None,
    )
    # Swap final classifier for custom num_classes
    num_classes = cfg["task"]["num_classes"]
    if hasattr(model, "fc"):
        model.fc = torch.nn.Linear(model.fc.in_features, num_classes)
    elif hasattr(model, "classifier"):
        model.classifier = torch.nn.Linear(model.classifier.in_features, num_classes)

    # --- datasets ---
    data_cfg = cfg["data"]
    transforms = None  # 프로젝트에서 augmentation config에 따라 구성
    train_set = ClassificationDataset(
        root=data_cfg["root"],
        split="train",
        split_file=data_cfg.get("split_file"),
        transforms=transforms,
    )
    val_set = ClassificationDataset(
        root=data_cfg["root"],
        split="val",
        split_file=data_cfg.get("split_file"),
        transforms=transforms,
    )

    return train_set, val_set, model, ClassificationTrainer
