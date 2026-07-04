"""OpenAI-compatible API adapter for NoteClaw.

This module provides a thin wrapper around the `AsyncOpenAI` SDK so backend
service modules can call text completion, embedding, vision, and image APIs
through a single interface.

It supports either one shared gateway for all tasks or different credentials
per task by using optional explicit overrides.
"""

from __future__ import annotations

import base64
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from typing import Final

from openai import AsyncOpenAI


_JSON_FENCE_RE: Final = re.compile(r"```json\s*(?P<json>.*?)\s*```", re.DOTALL)
_DEFAULT_CHAT_MODEL = "gpt-4o"
_DEFAULT_EMBED_MODEL = "text-embedding-3-small"
_DEFAULT_VISION_MODEL = "gpt-4o"
_DEFAULT_IMAGE_MODEL = "gpt-image-1"
_DEFAULT_OCR_MODEL = "deepseek-ai/DeepSeek-OCR"


class OpenAICompatError(RuntimeError):
    """Raised when OpenAI-compatible API calls are not usable."""


class MissingCredentialsError(OpenAICompatError):
    """Raised when an API key is required but not configured."""


@dataclass(frozen=True)
class ProviderEndpoint:
    """Single-capability endpoint settings."""

    api_key: str | None
    base_url: str | None
    model: str


@dataclass(frozen=True)
class OpenAICompatConfig:
    """Merged settings for all NoteClaw API capabilities."""

    chat: ProviderEndpoint
    embedding: ProviderEndpoint
    vision: ProviderEndpoint
    image: ProviderEndpoint
    ocr: ProviderEndpoint


def _first_non_empty(*values: str | None) -> str | None:
    for value in values:
        if value is None:
            continue
        text = value.strip()
        if text:
            return text
    return None


def _normalize_base_url(base_url: str | None) -> str | None:
    if not base_url:
        return None
    return base_url.strip().rstrip("/")


def _normalize_api_key(api_key: str | None) -> str:
    if not api_key:
        return "no-key"
    return api_key.strip()


def _resolve_openai_compat_config(
    *,
    openai_compat_base_url: str | None,
    openai_compat_api_key: str | None,
    llm_model: str | None,
    embedding_model: str | None,
    vision_model: str | None,
    image_model: str | None,
    ocr_model: str | None = None,
    chat_api_key: str | None = None,
    chat_base_url: str | None = None,
    chat_model: str | None = None,
    embedding_api_key: str | None = None,
    embedding_base_url: str | None = None,
    embedding_model_override: str | None = None,
    vision_api_key: str | None = None,
    vision_base_url: str | None = None,
    vision_model_override: str | None = None,
    image_api_key: str | None = None,
    image_base_url: str | None = None,
    image_model_override: str | None = None,
    ocr_api_key: str | None = None,
    ocr_base_url: str | None = None,
    ocr_model_override: str | None = None,
) -> OpenAICompatConfig:
    """Compose final endpoint configs with explicit overrides + fallback values."""

    resolved_chat = ProviderEndpoint(
        api_key=_first_non_empty(chat_api_key, openai_compat_api_key),
        base_url=_normalize_base_url(_first_non_empty(chat_base_url, openai_compat_base_url)),
        model=_first_non_empty(chat_model, llm_model, _DEFAULT_CHAT_MODEL),
    )

    resolved_embedding = ProviderEndpoint(
        api_key=_first_non_empty(embedding_api_key, openai_compat_api_key),
        base_url=_normalize_base_url(_first_non_empty(embedding_base_url, openai_compat_base_url)),
        model=_first_non_empty(embedding_model_override, embedding_model, _DEFAULT_EMBED_MODEL),
    )

    resolved_vision = ProviderEndpoint(
        api_key=_first_non_empty(vision_api_key, openai_compat_api_key),
        base_url=_normalize_base_url(_first_non_empty(vision_base_url, openai_compat_base_url)),
        model=_first_non_empty(vision_model_override, vision_model, _DEFAULT_VISION_MODEL),
    )

    resolved_image = ProviderEndpoint(
        api_key=_first_non_empty(image_api_key, openai_compat_api_key),
        base_url=_normalize_base_url(_first_non_empty(image_base_url, openai_compat_base_url)),
        model=_first_non_empty(image_model_override, image_model, _DEFAULT_IMAGE_MODEL),
    )

    resolved_ocr = ProviderEndpoint(
        api_key=_first_non_empty(ocr_api_key, openai_compat_api_key),
        base_url=_normalize_base_url(_first_non_empty(ocr_base_url, openai_compat_base_url)),
        model=_first_non_empty(ocr_model_override, ocr_model, _DEFAULT_OCR_MODEL),
    )

    return OpenAICompatConfig(
        chat=resolved_chat,
        embedding=resolved_embedding,
        vision=resolved_vision,
        image=resolved_image,
        ocr=resolved_ocr,
    )


def _ensure_credentials(endpoint: ProviderEndpoint, usage: str) -> str:
    if endpoint.api_key and endpoint.api_key.strip():
        return endpoint.api_key.strip()
    raise MissingCredentialsError(f"{usage} API key is missing for OpenAI-compatible call.")


def _parse_json_payload(payload: str) -> dict[str, Any]:
    """Best-effort parser for model-generated JSON."""

    text = payload.strip()
    if not text:
        raise ValueError("model returned empty response")

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    fenced = _JSON_FENCE_RE.search(text)
    if fenced is not None:
        try:
            return json.loads(fenced.group("json"))
        except json.JSONDecodeError as exc:
            raise ValueError("fenced-json parsing failed") from exc

    start = text.find("{")
    end = text.rfind("}")
    if start >= 0 and end > start:
        snippet = text[start : end + 1]
        try:
            return json.loads(snippet)
        except json.JSONDecodeError:
            pass

    raise ValueError("response is not JSON")


def _image_to_data_url(image_path: str) -> str:
    path = Path(image_path)
    if not path.exists() or not path.is_file():
        raise FileNotFoundError(f"image file not found: {image_path}")

    raw = path.read_bytes()
    suffix = path.suffix.removeprefix(".").lower() or "png"
    mime = f"image/{'jpeg' if suffix == 'jpg' else suffix}"
    encoded = base64.b64encode(raw).decode("ascii")
    return f"data:{mime};base64,{encoded}"


class NoteClawOpenAICompat:
    """OpenAI-compatible endpoint wrapper used by NoteClaw service layers."""

    def __init__(self, config: OpenAICompatConfig) -> None:
        self._config = config
        self._clients: dict[str, AsyncOpenAI] = {}

    @classmethod
    def from_env_like(
        cls,
        *,
        openai_compat_base_url: str | None = None,
        openai_compat_api_key: str | None = None,
        llm_model: str | None = None,
        embedding_model: str | None = None,
        vision_model: str | None = None,
        image_model: str | None = None,
        chat_api_key: str | None = None,
        chat_base_url: str | None = None,
        chat_model: str | None = None,
        embedding_api_key: str | None = None,
        embedding_base_url: str | None = None,
        embedding_model_override: str | None = None,
        vision_api_key: str | None = None,
        vision_base_url: str | None = None,
        vision_model_override: str | None = None,
        image_api_key: str | None = None,
        image_base_url: str | None = None,
        image_model_override: str | None = None,
        ocr_api_key: str | None = None,
        ocr_base_url: str | None = None,
        ocr_model: str | None = None,
        ocr_model_override: str | None = None,
    ) -> "NoteClawOpenAICompat":
        config = _resolve_openai_compat_config(
            openai_compat_base_url=openai_compat_base_url,
            openai_compat_api_key=openai_compat_api_key,
            llm_model=llm_model,
            embedding_model=embedding_model,
            vision_model=vision_model,
            image_model=image_model,
            chat_api_key=chat_api_key,
            chat_base_url=chat_base_url,
            chat_model=chat_model,
            embedding_api_key=embedding_api_key,
            embedding_base_url=embedding_base_url,
            embedding_model_override=embedding_model_override,
            vision_api_key=vision_api_key,
            vision_base_url=vision_base_url,
            vision_model_override=vision_model_override,
            image_api_key=image_api_key,
            image_base_url=image_base_url,
            image_model_override=image_model_override,
            ocr_api_key=ocr_api_key,
            ocr_base_url=ocr_base_url,
            ocr_model=ocr_model,
            ocr_model_override=ocr_model_override,
        )
        return cls(config)

    def _client(self, endpoint: ProviderEndpoint) -> AsyncOpenAI:
        key = f"{_normalize_base_url(endpoint.base_url) or 'default'}|{_normalize_api_key(endpoint.api_key)}"
        if key not in self._clients:
            self._clients[key] = AsyncOpenAI(
                api_key=_normalize_api_key(endpoint.api_key),
                base_url=endpoint.base_url,
                timeout=120,
            )
        return self._clients[key]

    async def complete_text(
        self,
        messages: list[dict[str, Any]],
        *,
        model: str | None = None,
        temperature: float = 0.2,
        max_tokens: int = 1024,
    ) -> str:
        endpoint = ProviderEndpoint(
            api_key=self._config.chat.api_key,
            base_url=self._config.chat.base_url,
            model=model or self._config.chat.model,
        )
        _ensure_credentials(endpoint, "Chat")

        response = await self._client(endpoint).chat.completions.create(
            model=endpoint.model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        choice = response.choices[0] if response.choices else None
        if not choice:
            return ""
        content = getattr(choice.message, "content", None)
        return content or ""

    async def complete_json(
        self,
        messages: list[dict[str, Any]],
        *,
        schema: dict[str, Any] | None = None,
        model: str | None = None,
        temperature: float = 0.2,
        max_tokens: int = 1024,
    ) -> dict[str, Any]:
        instruction = ""
        if schema is not None:
            instruction = (
                "\n\nReturn strict JSON only. "
                f"Field schema: {json.dumps(schema, ensure_ascii=False)}"
            )

        text = await self.complete_text(
            messages=[
                *messages,
                {"role": "system", "content": instruction},
            ],
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        try:
            return _parse_json_payload(text)
        except ValueError as exc:
            raise OpenAICompatError("failed to parse JSON from model output") from exc

    async def embed_texts(self, texts: list[str], *, model: str | None = None) -> list[list[float]]:
        endpoint = ProviderEndpoint(
            api_key=self._config.embedding.api_key,
            base_url=self._config.embedding.base_url,
            model=model or self._config.embedding.model,
        )
        _ensure_credentials(endpoint, "Embedding")
        client = self._client(endpoint)

        if not texts:
            return []

        response = await client.embeddings.create(model=endpoint.model, input=texts)
        ordered = sorted(response.data, key=lambda item: item.index)
        return [entry.embedding for entry in ordered]

    async def understand_image(
        self,
        image_path: str,
        ocr_text: str | None = None,
        *,
        model: str | None = None,
        extra_prompt: str | None = None,
        enable_ocr: bool = True,
    ) -> dict[str, Any]:
        endpoint = ProviderEndpoint(
            api_key=self._config.vision.api_key,
            base_url=self._config.vision.base_url,
            model=model or self._config.vision.model,
        )
        _ensure_credentials(endpoint, "Vision")
        client = self._client(endpoint)

        prompt = "Extract key information from the image with summary, key points, and tags."
        if extra_prompt:
            prompt = f"{prompt}\n{extra_prompt}"
        if enable_ocr and not ocr_text:
            try:
                ocr_text = await self.extract_image_text(image_path)
            except Exception:
                ocr_text = None
        if ocr_text:
            prompt = f"{prompt}\nOCR text: {ocr_text}"

        data_url = _image_to_data_url(image_path)
        response = await client.chat.completions.create(
            model=endpoint.model,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": data_url}},
                    ],
                }
            ],
            max_tokens=1024,
        )

        choice = response.choices[0] if response.choices else None
        if not choice:
            return {
                "summary": "",
                "tags": [],
                "raw": "",
            }

        content = getattr(choice.message, "content", "") or ""
        try:
            parsed = _parse_json_payload(content)
            if isinstance(parsed, dict):
                return parsed
        except Exception:
            pass

        return {
            "summary": content.strip(),
            "tags": [],
            "raw": content,
        }

    async def extract_image_text(
        self,
        image_path: str,
        *,
        model: str | None = None,
        extra_prompt: str | None = None,
        max_tokens: int = 1024,
    ) -> str:
        endpoint = ProviderEndpoint(
            api_key=self._config.ocr.api_key,
            base_url=self._config.ocr.base_url,
            model=model or self._config.ocr.model,
        )
        _ensure_credentials(endpoint, "OCR")
        client = self._client(endpoint)

        prompt = "识别图片中的全部文字，保留换行和段落。只返回纯文本，不要额外解释。"
        if extra_prompt:
            prompt = f"{prompt}\n{extra_prompt}"

        data_url = _image_to_data_url(image_path)
        response = await client.chat.completions.create(
            model=endpoint.model,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": data_url}},
                    ],
                }
            ],
            max_tokens=max_tokens,
        )

        choice = response.choices[0] if response.choices else None
        if not choice:
            return ""
        content = (getattr(choice.message, "content", None) or "").strip()
        if not content:
            return ""

        try:
            parsed = _parse_json_payload(content)
            if isinstance(parsed, dict):
                return str(
                    _first_non_empty(
                        parsed.get("text"),
                        parsed.get("content"),
                        parsed.get("result"),
                        parsed.get("ocr_text"),
                    )
                    or content
                )
        except Exception:
            return content

        return content

    async def generate_image(
        self,
        prompt: str,
        *,
        size: str = "1024x1024",
        model: str | None = None,
    ) -> str:
        endpoint = ProviderEndpoint(
            api_key=self._config.image.api_key,
            base_url=self._config.image.base_url,
            model=model or self._config.image.model,
        )
        _ensure_credentials(endpoint, "Image")
        client = self._client(endpoint)

        response = await client.images.generate(
            model=endpoint.model,
            prompt=prompt,
            size=size,
            n=1,
        )
        first = (response.data[0] if response.data else None)
        if first is None:
            raise OpenAICompatError("image API returned no data")
        image_url = getattr(first, "url", None)
        if image_url:
            return str(image_url)
        b64 = getattr(first, "b64_json", None)
        if b64:
            return f"data:image/png;base64,{b64}"
        raise OpenAICompatError("image API returned unsupported data format")
