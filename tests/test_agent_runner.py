from __future__ import annotations

import os
import unittest


class AgentRunnerTests(unittest.TestCase):
    def test_parse_agent_yaml_supports_system_block(self) -> None:
        from agent.runner import parse_agent_yaml

        cfg = parse_agent_yaml(
            "\n".join(
                [
                    "name: carrier-api-explorer",
                    "model: gpt-4o-mini",
                    "system: |",
                    "  You help explore the Carrier HVAC API.",
                    "  Be precise. Prefer curl examples.",
                    "",
                ]
            )
        )

        self.assertEqual(cfg["name"], "carrier-api-explorer")
        self.assertEqual(cfg["model"], "gpt-4o-mini")
        self.assertIn("Prefer curl examples.", cfg["system"])

    def test_build_responses_payload(self) -> None:
        from agent.openai_responses import build_responses_payload

        payload = build_responses_payload(
            model="gpt-4o-mini",
            system="You are concise.",
            user_input="Hello",
        )

        self.assertEqual(payload["model"], "gpt-4o-mini")
        self.assertEqual(payload["instructions"], "You are concise.")
        self.assertEqual(payload["input"], "Hello")

    def test_extract_output_text_from_response(self) -> None:
        from agent.openai_responses import extract_output_text

        data = {
            "output": [
                {
                    "type": "message",
                    "role": "assistant",
                    "content": [
                        {"type": "output_text", "text": "Hello"},
                        {"type": "output_text", "text": " world"},
                    ],
                }
            ]
        }

        self.assertEqual(extract_output_text(data), "Hello world")

    def test_agent_requires_openai_api_key(self) -> None:
        from agent.openai_responses import get_openai_api_key

        old = os.environ.pop("OPENAI_API_KEY", None)
        try:
            with self.assertRaises(ValueError):
                get_openai_api_key()
        finally:
            if old is not None:
                os.environ["OPENAI_API_KEY"] = old


if __name__ == "__main__":
    unittest.main()

