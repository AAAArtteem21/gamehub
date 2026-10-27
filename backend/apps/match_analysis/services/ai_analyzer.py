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

def analyze_dota_snapshot(snapshots: dict) -> tuple[dict, str]:
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
    d = snapshot.get("deltas") or {}
    r20 = snapshot.get("recent_20") or {}
    won = m.get("won")

    k = m.get("kills")
    deaths = m.get("deaths")
    a = m.get("assists")
    gpm = m.get("gpm")
    xpm = m.get("xpm")
    kd = m.get("kd")

    strengths, weaknesses, recs = [], [], []

    def add_s(title, detail, evidence):
        strengths.append({"title": title, "detail": detail, "evidence": str(evidence)})

    def add_w(title, detail, evidence):
        weaknesses.append({"title": title, "detail": detail, "evidence": str(evidence)})

    def add_r(priority, action, why):
        recs.append({"priority": priority, "action": action, "why": why})

    kd_delta = d.get("kd_vs_avg")
    if kd_delta is not None:
        if kd_delta >= 0.25:
            add_s("K/D выше формы", "Лучше обычного соотношения убийств к смертям.", f"KD {kd} vs {r20.get('avg_kd')} (Δ {kd_delta:+})")
        elif kd_delta <= -0.25:
            add_w("K/D ниже формы", "Хуже обычного K/D — больше смертей или меньше киллов.", f"KD {kd} vs {r20.get('avg_kd')} (Δ {kd_delta:+})")
            add_r(1, "Меньше соло-заходов до ключевых предметов", "K/D просел относительно нормы")

    death_delta = d.get("deaths_vs_avg")
    if death_delta is not None and death_delta >= 2:
        add_w("Много смертей", "Смертей больше, чем обычно.", f"Deaths {deaths} vs ср. {r20.get('avg_deaths')} (Δ {death_delta:+})")
        add_r(1, "Играй ближе к тиммейтам до 20 минуты", "Высокий death count")

    if deaths is not None and deaths >= 10:
        add_w("Очень высокий death count", f"{deaths} смертей в одном матче — сильный штраф по опыту и карте.", f"deaths={deaths}")

    kill_delta = d.get("kills_vs_avg")
    if kill_delta is not None and kill_delta <= -5:
        add_w("Мало убийств", "Килл-участие ниже обычного.", f"Kills {k} vs ср. {r20.get('avg_kills')} (Δ {kill_delta:+})")

    if k is not None and k == 0 and (deaths or 0) >= 5:
        add_w("0 убийств", "Нет киллов при большом числе смертей.", f"KDA {k}/{deaths}/{a}")
        add_r(2, "Ищи файты с напарником", "0 kills при высоком deaths")

    gpm_delta = d.get("gpm_vs_avg")
    if gpm_delta is not None:
        if gpm_delta >= 50:
            add_s("Сильный фарм", "GPM выше твоей формы.", f"GPM {gpm} vs {r20.get('avg_gpm')} (Δ {gpm_delta:+})")
        elif gpm_delta <= -50:
            add_w("Слабый фарм", "GPM заметно ниже обычного.", f"GPM {gpm} vs {r20.get('avg_gpm')} (Δ {gpm_delta:+})")
            add_r(2, "После смерти быстрее возвращайся на линию/лес", "GPM ниже формы")

    xpm_delta = d.get("xpm_vs_avg")
    if xpm_delta is not None and xpm_delta <= -80:
        add_w("Отставание по опыту", "XPM сильно ниже нормы.", f"XPM {xpm} vs {r20.get('avg_xpm')} (Δ {xpm_delta:+})")

    if won is True:
        add_s("Победа", "Матч выигран.", "won=true")
    elif won is False:
        add_w("Поражение", "Матч проигран.", "won=false")

    if not strengths and not weaknesses:
        add_w("Мало данных", "Недостаточно статистики для детального разбора.", "empty")

    if not recs:
        add_r(1, "Сравни deaths и GPM со средней формой в следующих 3 катках", "Нужна стабильность")

    score = 50
    if won is True:
        score += 12
    elif won is False:
        score -= 12
    if kd_delta is not None:
        score += 8 if kd_delta > 0.2 else (-8 if kd_delta < -0.2 else 0)
    if gpm_delta is not None:
        score += 5 if gpm_delta > 40 else (-5 if gpm_delta < -40 else 0)
    if deaths is not None and deaths >= 10:
        score -= 8
    score = max(0, min(100, score))

    if won is True and score >= 65:
        headline = "Победа, выше своей формы"
    elif won is True:
        headline = "Победа"
    elif won is False and score <= 45:
        headline = "Поражение, ниже формы"
    elif won is False:
        headline = "Поражение"
    else:
        headline = "Разбор матча"

    return {
        "headline": headline,
        "score_0_100": score,
        "strengths": strengths[:5],
        "weaknesses": weaknesses[:5],
        "recommendations": recs[:4],
        "one_liner": recs[0]["action"] if recs else "Смотри KDA и GPM относительно формы",
    }

