import importlib.util
import sys
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))


@unittest.skipUnless(importlib.util.find_spec("torch"), "PyTorch is an optional vision dependency")
class SegmentationTests(unittest.TestCase):
    def test_small_unet_preserves_spatial_shape_and_class_count(self) -> None:
        import torch

        from shepherd_ai.segmentation import build_small_unet

        model = build_small_unet(class_count=10, base_channels=4)
        output = model(torch.randn(2, 3, 64, 64))

        self.assertEqual(tuple(output.shape), (2, 10, 64, 64))

    def test_masked_bce_ignores_invalid_pixels(self) -> None:
        import torch

        from shepherd_ai.segmentation import masked_multilabel_bce

        logits = torch.zeros((1, 2, 1, 2), requires_grad=True)
        targets = torch.tensor([[[[1.0, 0.0]], [[0.0, 1.0]]]])
        valid_mask = torch.tensor([[[True, False]]])

        loss = masked_multilabel_bce(logits, targets, valid_mask)
        loss.backward()

        self.assertAlmostEqual(float(loss.detach()), 0.693147, places=5)
        self.assertEqual(float(logits.grad[0, 0, 0, 1]), 0.0)
        self.assertEqual(float(logits.grad[0, 1, 0, 1]), 0.0)

    def test_masked_bce_supports_positive_and_class_weights(self) -> None:
        import torch

        from shepherd_ai.segmentation import masked_multilabel_bce

        logits = torch.zeros((1, 3, 1, 1))
        targets = torch.tensor([[[[1.0]], [[1.0]], [[0.0]]]])
        valid_mask = torch.tensor([[[True]]])

        loss = masked_multilabel_bce(
            logits,
            targets,
            valid_mask,
            positive_weights=torch.tensor([2.0, 4.0, 1.0]),
            class_weights=torch.tensor([1.0, 0.0, 1.0]),
        )

        self.assertAlmostEqual(float(loss), 1.0397208, places=5)

    def test_class_balance_uses_train_labels_and_excludes_absent_classes(self) -> None:
        from shepherd_ai.segmentation import class_balance_from_label_audit

        balance = class_balance_from_label_audit(
            {
                "selected_splits": ["train"],
                "valid_pixels": 100,
                "positive_pixels": {"background": 80, "rare": 2, "absent": 0},
            },
            class_names=("background", "rare", "absent"),
            positive_weight_cap=20.0,
        )

        self.assertEqual(balance["positive_weights"], [1.0, 20.0, 1.0])
        self.assertEqual(balance["class_weights"], [1.0, 1.0, 0.0])
        self.assertEqual(balance["absent_classes"], ["absent"])

    def test_class_balance_rejects_validation_labels(self) -> None:
        from shepherd_ai.segmentation import class_balance_from_label_audit

        with self.assertRaisesRegex(ValueError, "train split only"):
            class_balance_from_label_audit(
                {
                    "selected_splits": ["train", "validation"],
                    "valid_pixels": 100,
                    "positive_pixels": {"background": 80},
                },
                class_names=("background",),
                positive_weight_cap=20.0,
            )


if __name__ == "__main__":
    unittest.main()
