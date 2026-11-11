import json
import urllib.request
import urllib.error
import re

from ..core.config import settings


def is_enabled() -> bool:
    return bool(settings.LLM_ENABLED and settings.LLM_BASE_URL and settings.LLM_API_KEY and settings.LLM_MODEL)


def chat(message: str, context: str = "") -> str | None:
    if not is_enabled():
        return None
    url = settings.LLM_BASE_URL.rstrip("/") + "/chat/completions"
    payload = {
        "model": settings.LLM_MODEL,
        "temperature": 0.2,
        "messages": [
            {"role": "system", "content": "你是工业视觉质检助手。请用自然、简洁、口语化的中文回答。不要使用 Markdown，不要使用星号、井号、反引号或项目符号；用完整句子和中文标点分段回答。只能根据提供的系统信息回答，不要编造检测结果。"},
            {"role": "user", "content": (context + "\n" if context else "") + message},
        ],
    }
    request = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers={"Authorization": f"Bearer {settings.LLM_API_KEY}", "Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(request, timeout=settings.LLM_TIMEOUT) as response:
            body = json.loads(response.read().decode("utf-8"))
        answer = body["choices"][0]["message"]["content"].strip()
        answer = re.sub(r"\*{1,3}", "", answer)
        answer = re.sub(r"^\s*[-•]\s*", "", answer, flags=re.MULTILINE)
        answer = re.sub(r"#{1,6}\s*", "", answer)
        answer = answer.replace("`", "")
        return answer.strip()
    except Exception as exc:
        print(f"LLM request failed, fallback to local assistant: {exc}")
        return None
