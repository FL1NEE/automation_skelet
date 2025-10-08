# -*- coding: utf-8 -*-
import re
import json
import requests
from typing import Any, Dict, Optional

API_KEY = "AIzaSyBa7D7aRpdPyv_M_1QecSUUqiIqVgGSx_Q"
URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-pro:generateContent?key={API_KEY}"
HEADERS = {"Content-Type": "application/json"}

PROMPT = """
Твоя задача сгенерировать промпт-вопрос минимум из 50000 символов
На тематику: Криптовалюта

Ответ дай строго в формате JSON:
{
  "prompt_len": "КОЛИЧЕСТВО СИМВОЛОВ В ТВОЕМ ПРОМПТ-ОТВЕТЕ",
  "prompt": "САМ ПРОМПТ ОТ 50000 СИМВОЛОВ МИНИМУМ НА АНГЛИЙСКОМ ЯЗЫКЕ"
}
"""

def generate_crypto_prompt() -> Optional[Dict[str, Any]]:
    """
    Отправляет запрос к Gemini и возвращает JSON с результатом.
    Возвращает:
        dict: Содержит поля "prompt_len" и "prompt"
        None: если произошла ошибка при запросе или парсинге
    """
    payload = {
        "contents": [
            {"parts": [{"text": PROMPT}]}
        ]
    }

    try:
        resp = requests.post(URL, headers=HEADERS, data=json.dumps(payload))
        resp.raise_for_status()
    except requests.RequestException as e:
        print(f"❌ Ошибка запроса к Gemini API: {e}")
        return None

    try:
        resp_json = resp.json()
        text = resp_json["candidates"][0]["content"]["parts"][0]["text"].strip()

        # Убираем markdown-ограждения ```json ... ```
        text = re.sub(r"^```[a-zA-Z]*\n?", "", text)
        text = re.sub(r"```$", "", text)

        # Находим первую фигурную скобку
        idx = text.find("{")
        if idx > 0:
            text = text[idx:]

        result = json.loads(text)
        return result

    except Exception as e:
        print(f"❌ Ошибка при обработке ответа: {e}")
        return None

# Пример запуска модуля
#if __name__ == "__main__":
#    data = generate_crypto_prompt()
#    if data:
#        print("✅ Успешно получен результат")
#        print(f"🔢 prompt_len: {data.get('prompt_len')}")
#        print(f"🧠 Первые 300 символов:\n{data.get('prompt', '')[:300]}...")
#    else:
#        print("⚠️ Ошибка при генерации промпта.")