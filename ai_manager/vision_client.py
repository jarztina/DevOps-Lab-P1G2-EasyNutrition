import base64
import logging
import os
import anthropic

logger = logging.getLogger(__name__)

JSON_EXAMPLE = """{
  "ingredients": [
    {"name": "rice", "quantity": "1 bowl", "confidence": 0.9},
    {"name": "egg", "quantity": "2", "confidence": 0.8}
  ]
}"""

class VisionClient:
    MAX_TOKENS = 4000 # room for a "thinking block" plus the JSON answer

    def __init__(self, client=None):
        self._client = client

    def _get_client(self) -> tuple[bool, object]:
        if self._client is not None:
            return True, self._client
        key = os.environ.get("ANTHROPIC_API_KEY", "")
        if not key:
            return False, "AI API key is not configured."
        return True, anthropic.Anthropic(api_key=key, timeout=30.0, max_retries=0)

    @staticmethod
    def build_prompt() -> str:
        """Write the instructions we send with the photo."""
        return (
            "You are a food-recognition assistant. Look at the photo of leftover food.\n"
            "List every separate food item or ingredient you can see. Use simple, common, "
            "singular English names (for example 'rice', 'egg', 'spring onion').\n"
            "Rules: quantity is short text like '1 bowl'. confidence is a number from 0 to 1. "
            "If no food is visible, return an empty list.\n"
            "Reply with ONLY a JSON object, no other text, in exactly this shape:\n"
            + JSON_EXAMPLE
        )

    @staticmethod
    def _first_text(message) -> str | None:
        """The answer may start with a 'thinking' block, so pick the first text block."""
        for block in message.content or []:
            if getattr(block, "type", "") == "text":
                return block.text
        return None

    def ask(self, image_bytes: bytes, media_type: str, prompt: str) -> tuple[bool, str]:
        """Send photo + prompt. Return the raw text of the answer, or an error message."""
        ok, client = self._get_client()
        if not ok:
            return False, client
            
        model = os.environ.get("AI_MODEL", "")
        if not model:
            return False, "AI model is not configured."
            
        image_b64 = base64.b64encode(image_bytes).decode("ascii")
        try:
            message = client.messages.create(
                model=model,
                max_tokens=self.MAX_TOKENS,
                messages=[{"role": "user", "content": [
                    {"type": "image", "source": {"type": "base64",
                                                 "media_type": media_type,
                                                 "data": image_b64}},
                    {"type": "text", "text": prompt},
                ]}],
            )
        except anthropic.APIConnectionError:
            return False, "Cannot reach the AI service (network problem or timeout)."
        except anthropic.APIStatusError as exc:
            logger.error("AI API status error %s", exc.status_code)
            return False, f"AI service error (status {exc.status_code})."
        except Exception:
            logger.exception("Unexpected error calling the AI API")
            return False, "Unexpected error while calling the AI service."
            
        text = self._first_text(message)
        if text is None:
            return False, "The AI service returned an empty answer."
        return True, text
