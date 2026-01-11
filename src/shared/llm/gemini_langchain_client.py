# src/shared/llm/gemini_langchain_client.py
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Dict, Optional

from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import PromptTemplate

load_dotenv()


@dataclass
class GeminiLangChainConfig:
    # Use LangChain-style model IDs (no "models/" prefix)
    model: str = os.getenv("GEMINI_MODEL", "gemini-2.0-flash-lite")

    # Lower temp is better for strict JSON outputs
    temperature: float = float(os.getenv("GEMINI_TEMPERATURE", "0.6"))

    timeout: int = int(os.getenv("GEMINI_TIMEOUT", "30"))
    max_retries: int = int(os.getenv("GEMINI_MAX_RETRIES", "2"))


class GeminiLangChainClient:
    """
    Thin wrapper around LangChain + Gemini.
    """

    def __init__(self, config: Optional[GeminiLangChainConfig] = None):
        self.config = config or GeminiLangChainConfig()

        # Hard kill for demos / quota protection
        if os.getenv("DISABLE_LLM", "false").lower() == "true":
            raise RuntimeError("LLM disabled by DISABLE_LLM=true")

        api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise RuntimeError("Missing API key. Put GOOGLE_API_KEY in your .env file.")

        self.llm = ChatGoogleGenerativeAI(
            model=self.config.model,
            google_api_key=api_key,
            temperature=self.config.temperature,
            timeout=self.config.timeout,
            max_retries=self.config.max_retries,
        )

    def generate(self, prompt_template: str, variables: Dict[str, Any]) -> str:
        prompt = PromptTemplate.from_template(prompt_template)
        text = prompt.format(**variables)  # string prompt
        resp = self.llm.invoke(text)
        return getattr(resp, "content", str(resp))

    def generate_raw(self, prompt: str) -> str:
        resp = self.llm.invoke(prompt)
        return getattr(resp, "content", str(resp))
