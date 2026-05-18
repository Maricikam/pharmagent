"""
agents/base.py — Base class for all PharmAgent AI agents.
"""

import json
import anthropic
from tools.pharmacy_tools import TOOL_DEFINITIONS, TOOL_FUNCTIONS


class BaseAgent:
    def __init__(self, name: str, system_prompt: str, model: str = "claude-haiku-4-5-20251001"):
        self.name = name
        self.system_prompt = system_prompt
        self.model = model
        self.client = anthropic.Anthropic()

    def run(self, user_message: str, max_iterations: int = 10) -> str:
        messages = [{"role": "user", "content": user_message}]
        iterations = 0

        while iterations < max_iterations:
            iterations += 1
            response = self.client.messages.create(
                model=self.model,
                max_tokens=2048,
                system=self.system_prompt,
                tools=TOOL_DEFINITIONS,
                messages=messages,
            )

            assistant_content = response.content
            messages.append({"role": "assistant", "content": assistant_content})

            if response.stop_reason == "end_turn":
                for block in assistant_content:
                    if hasattr(block, "text"):
                        return block.text
                return "(No text response)"

            if response.stop_reason == "tool_use":
                tool_results = []
                for block in assistant_content:
                    if block.type == "tool_use":
                        tool_name = block.name
                        tool_input = block.input
                        tool_use_id = block.id

                        print(f"  🔧 [{self.name}] calling tool: {tool_name}({json.dumps(tool_input)})")

                        if tool_name in TOOL_FUNCTIONS:
                            result = TOOL_FUNCTIONS[tool_name](**tool_input)
                        else:
                            result = {"error": f"Unknown tool: {tool_name}"}

                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": tool_use_id,
                            "content": json.dumps(result),
                        })

                messages.append({"role": "user", "content": tool_results})

        return f"[{self.name}] Max iterations reached without final response."