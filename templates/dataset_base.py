"""Vision dataset 공통 베이스.

프로젝트 dataset은 이 BaseVisionDataset을 상속하여 task-specific한 label 로딩만 구현.
복사 경로: src/<package>/datasets/base.py
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Optional, Sequence

import torch
from torch.utils.data import Dataset


@dataclass(frozen=True)
class Sample:
    """단일 샘플의 표준 컨테이너.

    image: (C, H, W) float tensor, normalized.
    target: task-specific — class index (classification), box dict (detection),
            mask tensor (segmentation), keypoints tensor (landmark), etc.
    meta: file_id, source path, original size 등 메타데이터. 재현성·디버깅용.
    """
    image: torch.Tensor
    target: Any
    meta: dict[str, Any]


class BaseVisionDataset(Dataset):
    """모든 vision dataset의 공통 베이스.

    서브클래스가 구현할 것:
        _list_samples() -> Sequence[dict]  # 각 dict는 {id, image_path, ...}
        _load_target(record: dict) -> Any  # task-specific label

    공통 제공:
        - split 파일 기반 index 로딩
        - augmentation pipeline 적용
        - Sample dataclass로 반환
    """

    def __init__(
        self,
        root: str | Path,
        split: str,
        split_file: Optional[str | Path] = None,
        transforms: Optional[Callable] = None,
    ):
        self.root = Path(root)
        self.split = split
        self.split_file = Path(split_file) if split_file else None
        self.transforms = transforms
        self.records: Sequence[dict] = self._list_samples()

    # --- subclass 구현 필수 ---

    def _list_samples(self) -> Sequence[dict]:
        """split에 해당하는 sample 메타데이터 목록을 반환.

        권장 구조:
            [{"id": "img_0001", "image_path": "data/.../img.png", ...}, ...]
        split_file이 있으면 그걸 기준으로 필터링.
        """
        raise NotImplementedError

    def _load_target(self, record: dict) -> Any:
        """record로부터 task-specific target을 로드."""
        raise NotImplementedError

    # --- 공통 구현 ---

    def _load_image(self, record: dict) -> torch.Tensor:
        """기본: PIL로 열어 (C, H, W) float tensor 반환.
        서브클래스가 multi-channel/3D 등 특수 포맷을 다루면 override.
        """
        from PIL import Image
        from torchvision.transforms.functional import to_tensor
        img = Image.open(record["image_path"]).convert("RGB")
        return to_tensor(img)

    def __len__(self) -> int:
        return len(self.records)

    def __getitem__(self, idx: int) -> Sample:
        record = self.records[idx]
        image = self._load_image(record)
        target = self._load_target(record)

        if self.transforms is not None:
            image, target = self.transforms(image, target)

        meta = {k: v for k, v in record.items() if k not in {"image_path"}}
        meta["index"] = idx
        return Sample(image=image, target=target, meta=meta)


def collate_samples(batch: Sequence[Sample]) -> dict[str, Any]:
    """DataLoader용 collate.

    variable-size target(검출 박스 등)이 있으면 서브클래스가 별도 collate 제공.
    """
    images = torch.stack([s.image for s in batch], dim=0)
    targets = [s.target for s in batch]
    metas = [s.meta for s in batch]
    return {"images": images, "targets": targets, "metas": metas}
