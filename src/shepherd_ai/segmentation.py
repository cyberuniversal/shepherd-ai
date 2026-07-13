"""PyTorch components for the Agriculture-Vision development baseline."""

from __future__ import annotations

from pathlib import Path
from typing import Sequence

import numpy as np

from shepherd_ai.vision import VisionManifestRecord, load_agriculture_vision_2017_target


def build_small_unet(*, class_count: int, base_channels: int = 16):
    """Build a compact U-Net without pretrained weights."""

    import torch
    from torch import nn

    class ConvBlock(nn.Module):
        def __init__(self, in_channels: int, out_channels: int) -> None:
            super().__init__()
            self.layers = nn.Sequential(
                nn.Conv2d(in_channels, out_channels, 3, padding=1, bias=False),
                nn.BatchNorm2d(out_channels),
                nn.ReLU(inplace=True),
                nn.Conv2d(out_channels, out_channels, 3, padding=1, bias=False),
                nn.BatchNorm2d(out_channels),
                nn.ReLU(inplace=True),
            )

        def forward(self, values):
            return self.layers(values)

    class SmallUNet(nn.Module):
        def __init__(self) -> None:
            super().__init__()
            b = base_channels
            self.encoder1 = ConvBlock(3, b)
            self.encoder2 = ConvBlock(b, b * 2)
            self.encoder3 = ConvBlock(b * 2, b * 4)
            self.pool = nn.MaxPool2d(2)
            self.bridge = ConvBlock(b * 4, b * 8)
            self.up3 = nn.ConvTranspose2d(b * 8, b * 4, 2, stride=2)
            self.decoder3 = ConvBlock(b * 8, b * 4)
            self.up2 = nn.ConvTranspose2d(b * 4, b * 2, 2, stride=2)
            self.decoder2 = ConvBlock(b * 4, b * 2)
            self.up1 = nn.ConvTranspose2d(b * 2, b, 2, stride=2)
            self.decoder1 = ConvBlock(b * 2, b)
            self.classifier = nn.Conv2d(b, class_count, 1)

        def forward(self, values):
            e1 = self.encoder1(values)
            e2 = self.encoder2(self.pool(e1))
            e3 = self.encoder3(self.pool(e2))
            bridge = self.bridge(self.pool(e3))
            d3 = self.decoder3(torch.cat((self.up3(bridge), e3), dim=1))
            d2 = self.decoder2(torch.cat((self.up2(d3), e2), dim=1))
            d1 = self.decoder1(torch.cat((self.up1(d2), e1), dim=1))
            return self.classifier(d1)

    if class_count < 2:
        raise ValueError("class_count must be at least 2")
    if base_channels < 1:
        raise ValueError("base_channels must be positive")
    return SmallUNet()


class AgricultureVisionDataset:
    """Load RGB tiles and aligned multilabel masks without augmentation."""

    def __init__(self, records: Sequence[VisionManifestRecord], labels_dir: str | Path) -> None:
        self.records = list(records)
        self.labels_dir = Path(labels_dir)

    def __len__(self) -> int:
        return len(self.records)

    def __getitem__(self, index: int):
        import torch
        from PIL import Image

        record = self.records[index]
        with Image.open(record.image_path) as image:
            rgb = np.asarray(image.convert("RGB"), dtype=np.float32) / 255.0
        target = load_agriculture_vision_2017_target(self.labels_dir, record.image_path.stem)
        if rgb.shape[:2] != target.valid_mask.shape:
            raise ValueError(f"RGB and target shape mismatch for {record.id}")
        return {
            "id": record.id,
            "image": torch.from_numpy(np.moveaxis(rgb, -1, 0).copy()),
            "target": torch.from_numpy(target.targets.astype(np.float32, copy=False)),
            "valid_mask": torch.from_numpy(target.valid_mask.copy()),
        }


def masked_multilabel_bce(logits, targets, valid_mask):
    """Average BCE over classes and evaluation-valid pixels only."""

    import torch.nn.functional as functional

    if logits.shape != targets.shape:
        raise ValueError("logits and targets must have identical shapes")
    if valid_mask.shape != logits.shape[:1] + logits.shape[2:]:
        raise ValueError("valid_mask must have shape (batch, height, width)")
    losses = functional.binary_cross_entropy_with_logits(logits, targets, reduction="none")
    included = valid_mask[:, None].to(dtype=losses.dtype)
    denominator = included.sum() * logits.shape[1]
    if denominator.item() == 0:
        raise ValueError("batch contains no valid pixels")
    return (losses * included).sum() / denominator
