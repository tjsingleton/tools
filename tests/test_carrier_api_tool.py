from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path


def _load_tool_module():
    repo_root = Path(__file__).resolve().parents[1]
    main_py = repo_root / "tools" / "carrier-api" / "main.py"
    spec = importlib.util.spec_from_file_location("carrier_api_tool_main", main_py)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Failed to load module from {main_py}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class CarrierApiToolTests(unittest.TestCase):
    def setUp(self) -> None:
        self.m = _load_tool_module()

    def test_build_url_merges_query_items(self) -> None:
        url = self.m.build_url("https://api.example.com", "/v1/me", ["a=1", "b=two"])
        self.assertEqual(url, "https://api.example.com/v1/me?a=1&b=two")

    def test_build_request_spec_includes_bearer_token_by_default(self) -> None:
        spec = self.m.build_request_spec(
            base_url="https://api.example.com",
            path="/v1/me",
            method="GET",
            token="tkn",
            header_items=[],
            query_items=[],
            json_body=None,
        )
        self.assertEqual(spec.headers["Authorization"], "Bearer tkn")

    def test_to_curl_includes_json_body_when_provided(self) -> None:
        spec = self.m.build_request_spec(
            base_url="https://api.example.com",
            path="/v1/foo",
            method="POST",
            token=None,
            header_items=[],
            query_items=[],
            json_body='{"a": 1}',
        )
        curl = self.m.to_curl(spec)
        self.assertIn("Content-Type: application/json", curl)
        self.assertIn("--data-binary", curl)


if __name__ == "__main__":
    unittest.main()
