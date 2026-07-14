"""Train a reproducible compact U-Net Agriculture-Vision development baseline."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import random
import sys

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from shepherd_ai.segmentation import (  # noqa: E402
    AgricultureVisionDataset,
    build_small_unet,
    class_balance_from_label_audit,
    masked_multilabel_bce,
    masked_multilabel_soft_dice_loss,
)
from shepherd_ai.vision import (  # noqa: E402
    AGRICULTURE_VISION_2017_CLASSES,
    load_vision_manifest,
    modified_multilabel_iou,
    require_cuda_device,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--dataset-root", required=True)
    parser.add_argument("--labels-dir", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--epochs", type=int, default=3)
    parser.add_argument("--batch-size", type=int, default=4)
    parser.add_argument("--learning-rate", type=float, default=1e-3)
    parser.add_argument("--base-channels", type=int, default=16)
    parser.add_argument("--seed", type=int, default=17)
    parser.add_argument("--num-workers", type=int, default=2)
    parser.add_argument(
        "--device",
        choices=("cuda", "cpu"),
        default="cuda",
        help="Training device. CUDA remains the default for research runs.",
    )
    parser.add_argument("--required-device-substring", default="T4")
    parser.add_argument(
        "--train-label-audit",
        help="Train-only label-audit JSON used to derive class balance weights.",
    )
    parser.add_argument(
        "--positive-weight-cap",
        type=float,
        default=20.0,
        help="Maximum negative-to-positive ratio when a train label audit is supplied.",
    )
    parser.add_argument(
        "--loss",
        choices=("bce", "bce-dice"),
        default="bce",
        help="Training objective. bce-dice requires a train-only label audit.",
    )
    parser.add_argument(
        "--dice-weight",
        type=float,
        default=1.0,
        help="Multiplier for anomaly-only soft Dice when --loss=bce-dice.",
    )
    parser.add_argument("--resume", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.epochs < 1 or args.batch_size < 1 or args.learning_rate <= 0:
        raise SystemExit("epochs, batch-size, and learning-rate must be positive")
    if args.dice_weight <= 0:
        raise SystemExit("dice-weight must be positive")
    if args.loss == "bce-dice" and not args.train_label_audit:
        raise SystemExit("--loss=bce-dice requires --train-label-audit")

    import torch
    from torch.utils.data import DataLoader

    _set_seed(args.seed, torch)
    if args.device == "cuda":
        device_metadata = require_cuda_device(args.required_device_substring, torch)
        device = torch.device("cuda:0")
    else:
        device_metadata = {
            "cuda_available": torch.cuda.is_available(),
            "cuda_device_count": torch.cuda.device_count(),
            "cuda_device_names": [
                torch.cuda.get_device_name(index) for index in range(torch.cuda.device_count())
            ],
            "required_device_substring": None,
            "selected_device": "cpu",
        }
        device = torch.device("cpu")
    records = load_vision_manifest(args.manifest, dataset_root=args.dataset_root)
    train_records = [record for record in records if record.split == "train"]
    validation_records = [record for record in records if record.split == "validation"]
    if not train_records or not validation_records:
        raise SystemExit("manifest must contain non-empty train and validation splits")

    generator = torch.Generator().manual_seed(args.seed)
    train_loader = DataLoader(
        AgricultureVisionDataset(train_records, args.labels_dir),
        batch_size=args.batch_size,
        shuffle=True,
        num_workers=args.num_workers,
        pin_memory=device.type == "cuda",
        generator=generator,
    )
    validation_loader = DataLoader(
        AgricultureVisionDataset(validation_records, args.labels_dir),
        batch_size=args.batch_size,
        shuffle=False,
        num_workers=args.num_workers,
        pin_memory=device.type == "cuda",
    )
    class_balance = None
    positive_weights = None
    class_weights = None
    dice_class_weights = None
    if args.train_label_audit:
        audit = json.loads(Path(args.train_label_audit).read_text(encoding="utf-8"))
        class_balance = class_balance_from_label_audit(
            audit,
            class_names=AGRICULTURE_VISION_2017_CLASSES,
            positive_weight_cap=args.positive_weight_cap,
        )
        positive_weights = torch.tensor(
            class_balance["positive_weights"], dtype=torch.float32, device=device
        )
        class_weights = torch.tensor(
            class_balance["class_weights"], dtype=torch.float32, device=device
        )
        if args.loss == "bce-dice":
            dice_class_weights = class_weights.clone()
            dice_class_weights[0] = 0.0
            positive_weights = None
            class_weights = None
    model = build_small_unet(
        class_count=len(AGRICULTURE_VISION_2017_CLASSES),
        base_channels=args.base_channels,
    ).to(device)
    optimizer = torch.optim.Adam(model.parameters(), lr=args.learning_rate)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    last_checkpoint = output_dir / "last.pt"
    best_checkpoint = output_dir / "best.pt"
    start_epoch = 0
    best_miou = -1.0
    history: list[dict] = []
    if args.resume and last_checkpoint.is_file():
        checkpoint = torch.load(last_checkpoint, map_location=device, weights_only=False)
        model.load_state_dict(checkpoint["model_state_dict"])
        optimizer.load_state_dict(checkpoint["optimizer_state_dict"])
        start_epoch = int(checkpoint["epoch"]) + 1
        best_miou = float(checkpoint["best_validation_modified_miou"])
        history = list(checkpoint.get("history", []))

    config = {
        "model": "small_unet_from_scratch",
        "class_names": list(AGRICULTURE_VISION_2017_CLASSES),
        "loss": args.loss,
        "dice_weight": args.dice_weight if args.loss == "bce-dice" else None,
        "dice_scope": "train-present_anomaly_classes" if args.loss == "bce-dice" else None,
        "input_normalization": "uint8_rgb_divided_by_255",
        "epochs_requested": args.epochs,
        "batch_size": args.batch_size,
        "learning_rate": args.learning_rate,
        "base_channels": args.base_channels,
        "seed": args.seed,
        "num_workers": args.num_workers,
        "train_records": len(train_records),
        "validation_records": len(validation_records),
        "test_records_used": 0,
        "manifest": args.manifest,
        "dataset_root": args.dataset_root,
        "labels_dir": args.labels_dir,
        "device": device_metadata,
        "selected_device": str(device),
        "torch_version": torch.__version__,
        "numpy_version": np.__version__,
        "class_balance": class_balance,
        "train_label_audit": args.train_label_audit,
    }
    (output_dir / "training_config.json").write_text(
        json.dumps(config, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    for epoch in range(start_epoch, args.epochs):
        model.train()
        train_loss_sum = 0.0
        batches = 0
        for batch in train_loader:
            images = batch["image"].to(device, non_blocking=True)
            targets = batch["target"].to(device, non_blocking=True)
            valid_mask = batch["valid_mask"].to(device, non_blocking=True)
            optimizer.zero_grad(set_to_none=True)
            logits = model(images)
            loss = _training_objective(
                logits,
                targets,
                valid_mask,
                loss_name=args.loss,
                dice_weight=args.dice_weight,
                positive_weights=positive_weights,
                class_weights=class_weights,
                dice_class_weights=dice_class_weights,
            )
            loss.backward()
            optimizer.step()
            train_loss_sum += float(loss.detach().cpu())
            batches += 1

        validation = _evaluate(
            model,
            validation_loader,
            device,
            torch,
            positive_weights=positive_weights,
            class_weights=class_weights,
            loss_name=args.loss,
            dice_weight=args.dice_weight,
            dice_class_weights=dice_class_weights,
        )
        epoch_record = {
            "epoch": epoch,
            "train_loss": train_loss_sum / max(batches, 1),
            **validation,
        }
        history.append(epoch_record)
        improved = validation["validation_modified_miou"] > best_miou
        best_miou = max(best_miou, validation["validation_modified_miou"])
        checkpoint = {
            "epoch": epoch,
            "model_state_dict": model.state_dict(),
            "optimizer_state_dict": optimizer.state_dict(),
            "best_validation_modified_miou": best_miou,
            "history": history,
            "config": config,
        }
        torch.save(checkpoint, last_checkpoint)
        if improved:
            torch.save(checkpoint, best_checkpoint)
        metrics = {
            "generated_at_utc": datetime.now(timezone.utc).isoformat(),
            "status": "development_baseline_not_final_benchmark",
            "best_validation_modified_miou": best_miou,
            "history": history,
            "research_note": (
                "Validation-only development result. Test labels were not loaded. "
                "Do not report as final Agriculture-Vision benchmark performance."
            ),
        }
        (output_dir / "metrics.json").write_text(
            json.dumps(metrics, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        print(json.dumps(epoch_record, sort_keys=True), flush=True)


def _evaluate(
    model,
    data_loader,
    device,
    torch_module,
    *,
    positive_weights=None,
    class_weights=None,
    loss_name="bce",
    dice_weight=1.0,
    dice_class_weights=None,
) -> dict:
    model.eval()
    confusion = np.zeros(
        (len(AGRICULTURE_VISION_2017_CLASSES), len(AGRICULTURE_VISION_2017_CLASSES)),
        dtype=np.int64,
    )
    loss_sum = 0.0
    objective_loss_sum = 0.0
    batches = 0
    valid_pixels = 0
    with torch_module.no_grad():
        for batch in data_loader:
            images = batch["image"].to(device, non_blocking=True)
            targets = batch["target"].to(device, non_blocking=True)
            valid_mask = batch["valid_mask"].to(device, non_blocking=True)
            logits = model(images)
            loss_sum += float(masked_multilabel_bce(logits, targets, valid_mask).cpu())
            objective_loss_sum += float(
                _training_objective(
                    logits,
                    targets,
                    valid_mask,
                    loss_name=loss_name,
                    dice_weight=dice_weight,
                    positive_weights=positive_weights,
                    class_weights=class_weights,
                    dice_class_weights=dice_class_weights,
                ).cpu()
            )
            predictions = logits.argmax(dim=1).cpu().numpy()
            target_values = targets.cpu().numpy().astype(bool)
            valid_values = valid_mask.cpu().numpy().astype(bool)
            for index in range(predictions.shape[0]):
                result = modified_multilabel_iou(
                    predictions[index], target_values[index], valid_mask=valid_values[index]
                )
                confusion += result.confusion_matrix
                valid_pixels += result.valid_pixels
            batches += 1
    diagonal = np.diag(confusion)
    union = confusion.sum(axis=1) + confusion.sum(axis=0) - diagonal
    per_class = [None if value == 0 else float(diagonal[i] / value) for i, value in enumerate(union)]
    evaluated = [value for value in per_class if value is not None]
    return {
        "validation_loss": loss_sum / max(batches, 1),
        "validation_objective_loss": objective_loss_sum / max(batches, 1),
        "validation_modified_miou": float(np.mean(evaluated)) if evaluated else 0.0,
        "validation_per_class_iou": dict(zip(AGRICULTURE_VISION_2017_CLASSES, per_class)),
        "validation_confusion_matrix": confusion.tolist(),
        "validation_valid_pixels": valid_pixels,
    }


def _training_objective(
    logits,
    targets,
    valid_mask,
    *,
    loss_name,
    dice_weight,
    positive_weights,
    class_weights,
    dice_class_weights,
):
    bce = masked_multilabel_bce(
        logits,
        targets,
        valid_mask,
        positive_weights=positive_weights,
        class_weights=class_weights,
    )
    if loss_name == "bce":
        return bce
    if loss_name != "bce-dice":
        raise ValueError(f"unsupported loss: {loss_name}")
    dice = masked_multilabel_soft_dice_loss(
        logits,
        targets,
        valid_mask,
        class_weights=dice_class_weights,
    )
    return bce + (dice_weight * dice)


def _set_seed(seed: int, torch_module) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch_module.manual_seed(seed)
    torch_module.cuda.manual_seed_all(seed)
    torch_module.backends.cudnn.deterministic = True
    torch_module.backends.cudnn.benchmark = False


if __name__ == "__main__":
    main()
