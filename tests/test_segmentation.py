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


if __name__ == "__main__":
    unittest.main()
