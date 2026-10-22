from __future__ import annotations

import json
import logging
from django.conf import settings

logger = logging.getLogger(__name__)

REPORT_SCHEMA_HINT = """
Верни ТОЛЬКО JSON:
{
  "headline": "string",
  "score_0_100": 0-100,
  "strengths": [{"title": "", "detail": "", "evidence": ""}],
  "weaknesses": [{"title": "", "detail": "", "evidence": ""}],
  "recommendations": [{"priority": 1, "action": "", "why": ""}],
  "one_liner": "string"
}
Анализируй только факты из input. Не выдумывай vision/item timings, если их нет в limits/data.
Пиши по-русски.
"""

def analyze_dota_snapshots(snapshots: dict) -> tuple[dict, str]:
    api_key = getattr(settings, "OPEN_API_KEY", "") or ""
    model = getattr(settings, "OPENAI_MODEL", "gpt-40-mini")

    if not api_key:
        return _heuristic_report(snapshots), "heuristic"

    try:
        from openai import OpenAI

        client = OpenAI(api_key=api_key)
        resp = client.chat.complections.create(
            model=model,
            temperature=0.3,
            response_format={"type": "json_object"},
            mesages=[
                {
                    "role": "system",
                    "content": "ты аналатик Dota 2." + REPORT_SCHEMA_HINT,
                },
                {
                    "role": "user",
                    "content": json.dumps(snapshots, ensure_ascii=False),
                },
            ],
        )
        text = resp.choices[0].message.content or "{}"
        report = json.loads(text)
        return report, model
    except Exception as e:
        logger.exception("LLM analysis failed")
        report = _heuristic_report(snapshots)
        report["headline"] = report.get("headline") or "Базовый разбор (AI недоступен)"
        report["_error"] = str(e)[:200]
        return report, "heuristic"

def _heuristic_report(snapshot: dict) -> dict:
    m = snapshot.get("match") or {}
    d = snapshot.get("detals") or {}
    won = m.get("won")

    strengths, weaknesses, recs = [], [], []

    if d.get("kd_vs_avg", 0) >= 0.2:
        strengths.append({
            "title": "K/D выше обычного",
            "detail": "В этом матче соотношение убийств к смертям лучше среднего за последние игры.",
            "evidence": f"KD {m.get('kd')} vs avg {snapshot.get('recent_20', {}).get('avg_kd')}",
        })
    if d.get("kd_vs_avg", 0) <= -0.2:
        weaknesses.append({
            "title": "K/D ниже формы",
            "detail": "Больше смертей или меньше убийств, чем обычно.",
            "evidence": f"KD {m.get('kd')} vs avg {snapshot.get('recent_20', {}).get('avg_kd')}",
        })
        recs.append({
            "priority": 1,
            "action": "Играй осторожнее до пика предметов, меньше соло-заходов",
            "why": "Смерти выше среднего относительно твоей формы",
        })

    if d.get("gpm_vs_avg", 0) >= 40:
        strengths.append({
            "title": "Хороший фарм",
            "detail": "GPM заметно выше среднего.",
            "evidence": f"GPM {m.get('gpm')} vs avg {snapshot.get('recent_20', {}).get('avg_gpm')}",
        })
    elif d.get("gpm_vs_avg", 0) <= -40:
        weaknesses.append({
            "title": "Фарм ниже обычного",
            "detail": "Меньше золота в минуту, чем в последних матчах.",
            "evidence": f"GPM {m.get('gpm')} vs avg {snapshot.get('recent_20', {}).get('avg_gpm')}",
        })
        recs.append({
            "priority": 2,
            "action": "Держи стек/кейс/волны стабильнее, не теряй ленту после смерти",
            "why": "GPM просел относительно формы",
        })

    if not strengths and won:
        strengths.append({
            "title": "Победа",
            "detail": "Матч выигран.",
            "evidence": "won=true",
        })
    if not weaknesses and not won:
        weaknesses.append({
            "title": "Поражение",
            "detail": "Матч проигран — сверь deaths и участие в файтах.",
            "evidence": "won=false",
        })

    if not recs:
        recs.append({
            "priority": 1,
            "action": "Сравни deaths и GPM со своей средней формой в следующих 3 катках",
            "why": "Нужна стабильность показателей",
        })

    score = 50
    score += 10 if won else -10
    score += 8 if d.get("kd_vs_avg", 0) > 0.15 else 0
    score -= 8 if d.get("kd_vs_avg", 0) < -0.15 else 0
    score = max(0, min(100, score))

    return {
        "headline": "Победа выше своей  формы" if won and score >= 60 else(
            "Поражение, ниже формы" if not won and score < 50 else "Разбор матча"
        ),
        "score_0_100": score,
        "strengths": strengths[:4],
        "weakness": weaknesses[:4],
        "recommendations": recs[:4],
        "one_liner": recs[0]["action"] if recs else "Смотрим  форму по KDA и GPM",
    }
