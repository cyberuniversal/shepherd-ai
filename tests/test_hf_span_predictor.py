from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from shepherd_ai.hf_span_predictor import HfTokenClassifierSpanPredictor  # noqa: E402


class _FakeTensor:
    def __init__(self, value):
        self.value = value

    def to(self, _device):
        return self

    def argmax(self, *, dim):
        assert dim == -1
        return self

    def __getitem__(self, index):
        assert index == 0
        return self

    def detach(self):
        return self

    def cpu(self):
        return self

    def tolist(self):
        return self.value


class _FakeEncoding(dict):
    def word_ids(self, *, batch_index):
        assert batch_index == 0
        return [None, 0, 1, 2, 3, None]


class _FakeTokenizer:
    def __call__(self, tokens, **kwargs):
        assert tokens == ["Inspect", "the", "greenhouse", "."]
        assert kwargs["is_split_into_words"]
        return _FakeEncoding(input_ids=_FakeTensor([]))


class _FakeModel:
    def __call__(self, **_inputs):
        return type(
            "Output",
            (),
            {"logits": _FakeTensor([0, 1, 0, 3, 0, 0])},
        )()


class _InferenceMode:
    def __enter__(self):
        return None

    def __exit__(self, *_args):
        return False


class _FakeTorch:
    @staticmethod
    def inference_mode():
        return _InferenceMode()


class HfSpanPredictorTests(unittest.TestCase):
    def test_predict_entities_aligns_first_subtokens_to_word_offsets(self) -> None:
        predictor = HfTokenClassifierSpanPredictor(
            model_name="fake",
            model=_FakeModel(),
            tokenizer=_FakeTokenizer(),
            id2label={0: "O", 1: "B-action", 3: "B-target"},
            torch_module=_FakeTorch(),
            device="cpu",
            runtime_metadata={},
        )

        self.assertEqual(
            predictor.predict_entities("Inspect the greenhouse."),
            [["action", 0, 7], ["target", 12, 22]],
        )


if __name__ == "__main__":
    unittest.main()
