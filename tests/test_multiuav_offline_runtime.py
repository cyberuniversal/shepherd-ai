import os
import socket
import unittest

from shepherd_ai.multiuav_offline_runtime import (
    NetworkIsolationError,
    offline_inference_guard,
)


class MultiUavOfflineRuntimeTests(unittest.TestCase):
    def test_guard_blocks_non_loopback_name_resolution(self) -> None:
        with offline_inference_guard():
            with self.assertRaisesRegex(
                NetworkIsolationError,
                "non-loopback network access blocked",
            ):
                socket.getaddrinfo("example.com", 443)

    def test_guard_allows_loopback_name_resolution(self) -> None:
        with offline_inference_guard():
            results = socket.getaddrinfo("localhost", 80)

        self.assertTrue(results)

    def test_guard_sets_and_restores_offline_environment(self) -> None:
        names = ("HF_HUB_OFFLINE", "TRANSFORMERS_OFFLINE")
        previous = {name: os.environ.get(name) for name in names}
        os.environ["HF_HUB_OFFLINE"] = "prior"
        os.environ.pop("TRANSFORMERS_OFFLINE", None)
        try:
            with offline_inference_guard():
                self.assertEqual(os.environ["HF_HUB_OFFLINE"], "1")
                self.assertEqual(os.environ["TRANSFORMERS_OFFLINE"], "1")
            self.assertEqual(os.environ["HF_HUB_OFFLINE"], "prior")
            self.assertNotIn("TRANSFORMERS_OFFLINE", os.environ)
        finally:
            for name, value in previous.items():
                if value is None:
                    os.environ.pop(name, None)
                else:
                    os.environ[name] = value

    def test_guard_blocks_direct_non_loopback_connect_before_io(self) -> None:
        candidate = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            with offline_inference_guard():
                with self.assertRaises(NetworkIsolationError):
                    candidate.connect(("203.0.113.1", 443))
        finally:
            candidate.close()

    def test_guard_blocks_create_connection_before_io(self) -> None:
        with offline_inference_guard():
            with self.assertRaises(NetworkIsolationError):
                socket.create_connection(("203.0.113.1", 443))


if __name__ == "__main__":
    unittest.main()
