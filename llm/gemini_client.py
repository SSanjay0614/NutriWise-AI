"""
Gemini LLM client (REST) for meal parsing, off-dataset food estimation,
food guidance, and the analysis summary.

Exposes the same methods the app relies on: check_connection, parse_meal,
estimate_food_nutrition, food_guidance, narrative. Uses the Generative Language
REST API so no extra SDK dependency is needed.
"""
import json
import requests
from typing import Optional
from models.schemas import ParsedMeal, ParsedFood, LLMFoodNutritionEstimate

API_ROOT = "https://generativelanguage.googleapis.com/v1beta/models"

# Lines/labels that are prompt scaffolding or model reasoning, not the summary.
_DROP_PREFIXES = ("sentence", "focus", "encouragement", "*", "-", "•", ">", "#",
                  "supportive diabetes", "weekly summary", "no medical", "plain text",
                  "3-4", "ai coach", "days tracked", "avg ", "active days",
                  "glucose trend", "days in range")


def _clean_summary(text: str) -> str:
    """Strip reasoning/scaffolding and keep the actual prose summary."""
    if not text:
        return ""
    text = text.strip()
    # If a JSON summary slipped through as text, pull it out.
    if '"summary"' in text:
        import re
        m = re.search(r'"summary"\s*:\s*"([^"]+)"', text)
        if m:
            return m.group(1).strip()
    kept = []
    for raw in text.splitlines():
        line = raw.strip().lstrip("*->•# ").strip()
        if not line:
            continue
        low = line.lower()
        if any(low.startswith(p) for p in _DROP_PREFIXES):
            continue
        if low.endswith(":") and len(line) < 40:   # section headers like "Focus:"
            continue
        kept.append(line)
    cleaned = " ".join(kept).strip()
    # Collapse whitespace.
    return " ".join(cleaned.split())


class GeminiClient:
    def __init__(self, api_key: str, model: str = "gemini-2.0-flash"):
        self.api_key = api_key
        # Accept "gemini-2.0-flash" or "models/gemini-2.0-flash".
        self.model = (model or "gemini-2.0-flash").strip().removeprefix("models/")
        self.last_raw_response: Optional[str] = None

    def check_connection(self) -> bool:
        """Configured if an API key is present (no network round-trip)."""
        return bool(self.api_key)

    def _generate(self, prompt: str, as_json: bool = True, max_tokens: int = 1024) -> Optional[str]:
        if not self.api_key:
            return None
        url = f"{API_ROOT}/{self.model}:generateContent?key={self.api_key}"

        def _call(use_json: bool):
            gen = {"maxOutputTokens": max_tokens, "temperature": 0.4}
            if use_json:
                gen["responseMimeType"] = "application/json"
            body = {"contents": [{"parts": [{"text": prompt}]}], "generationConfig": gen}
            return requests.post(url, json=body, timeout=30)

        try:
            r = _call(as_json)
            # Some models (e.g. Gemma) reject JSON response mode -> retry plain.
            if r.status_code != 200 and as_json:
                r = _call(False)
            if r.status_code != 200:
                print(f"[Gemini] error {r.status_code}: {r.text[:200]}")
                return None
            data = r.json()
            parts = (data.get("candidates") or [{}])[0].get("content", {}).get("parts", [{}])
            text = (parts[0].get("text") or "").strip()
            self.last_raw_response = text
            return text or None
        except Exception as exc:
            print(f"[Gemini] request failed: {exc}")
            return None

    @staticmethod
    def _json_block(text: str) -> Optional[dict]:
        if not text:
            return None
        start, end = text.find("{"), text.rfind("}") + 1
        if start == -1 or end == 0:
            return None
        try:
            return json.loads(text[start:end])
        except (json.JSONDecodeError, ValueError):
            return None

    def parse_meal(self, user_input: str) -> Optional[ParsedMeal]:
        if not user_input or not user_input.strip():
            return None
        prompt = (
            "Extract foods and quantities from this meal description. Return ONLY "
            'JSON: {"foods":[{"food_name":"name","quantity":number,"unit":"g|piece|cup|bowl|glass"}]}.'
            " Use simple food names; default unit g; default quantity 1.\n"
            f'Meal: "{user_input}"'
        )
        data = self._json_block(self._generate(prompt) or "")
        if not data or "foods" not in data:
            return None
        foods = []
        for fd in data["foods"]:
            try:
                pf = ParsedFood(food_name=str(fd.get("food_name", "")).strip(),
                                quantity=float(fd.get("quantity", 1)),
                                unit=str(fd.get("unit", "g")).strip())
                if pf.food_name:
                    foods.append(pf)
            except (ValueError, TypeError):
                continue
        return ParsedMeal(foods=foods) if foods else None

    def estimate_food_nutrition(self, food_name: str, quantity: float = 1.0,
                                unit: str = "serving") -> Optional[LLMFoodNutritionEstimate]:
        if not food_name or not food_name.strip():
            return None
        prompt = (
            "Estimate approximate nutrition for the TOTAL amount described. Return ONLY JSON: "
            '{"food_name":"proper name","quantity":%s,"unit":"%s","serving_size_g":number,'
            '"calories_kcal":number,"protein_g":number,"carbohydrate_g":number,"fat_g":number,'
            '"fiber_g":number,"sugar_g":number,"sodium_mg":number,"calcium_mg":number,'
            '"iron_mg":number,"potassium_mg":number,"glycemic_index":number}. '
            "glycemic_index is a 0-100 estimate. Use realistic non-zero values.\n"
            'Food: "%s" (%s %s)' % (quantity, unit, food_name, quantity, unit)
        )
        data = self._json_block(self._generate(prompt) or "")
        if not data:
            return None
        data.setdefault("food_name", food_name)
        data.setdefault("quantity", quantity)
        data.setdefault("unit", unit)
        data["source"] = "LLM estimate"
        try:
            return LLMFoodNutritionEstimate(**data)
        except Exception:
            return None

    def food_guidance(self, food_name: str) -> Optional[dict]:
        if not food_name or not food_name.strip():
            return None
        prompt = (
            "For the food below return ONLY JSON: "
            '{"food_name":"proper name","category":"short","glycemic_index":number,'
            '"diabetes_friendly":true/false,"alternatives":["a","b","c"],"note":"one sentence"}. '
            "alternatives are lower-GI, higher-fiber foods a diabetic could eat instead.\n"
            f'Food: "{food_name}"'
        )
        data = self._json_block(self._generate(prompt) or "")
        if data:
            data.setdefault("food_name", food_name)
        return data

    def narrative(self, context: str) -> Optional[str]:
        prompt = (
            "You are a supportive diabetes diet coach. From the weekly summary below, "
            "write a short encouraging summary (3-4 sentences) covering progress and the "
            "single most important focus for next week. No medical or insulin advice. "
            'Return ONLY compact JSON: {"summary": "your text here"} and nothing else.\n\n'
            + context
        )
        text = self._generate(prompt, as_json=True, max_tokens=400)
        data = self._json_block(text or "")
        if data and isinstance(data.get("summary"), str) and data["summary"].strip():
            return _clean_summary(data["summary"])
        return _clean_summary(text or "") or None
