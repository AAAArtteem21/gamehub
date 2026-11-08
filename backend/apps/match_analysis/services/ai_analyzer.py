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

def _heuristic_faceit(snapshot: dict) -> dict:
    match = snapshot.get("match") or {}
    recent = snapshot.get("recent_20") or {}
    deltas = snapshot.get("deltas") or {}

    won = match.get("won")
    kills = match.get("kills")
    deaths = match.get("deaths")
    assists = match.get("assists")
    kd = match.get("kd")
    hs = match.get("headshots") or match.get("hs_percent")
    mvps = match.get("mvps")
    map_name = match.get("map") or ""
    score = match.get("score") or ""

    try:
        kd = float(kd) if kd is not None else None
    except (TypeError, ValueError):
        kd = None
    if kd is None and kills is not None and deaths is not None:
        try:
            kd = float(kills) / max(float(deaths), 1.0)
        except (TypeError, ValueError):
            kd = None

    avg_kd = recent.get("avg_kd")
    avg_kills = recent.get("avg_kills")
    avg_deaths = recent.get("avg_deaths")
    winrate = recent.get("winrate")

    kd_vs = deltas.get("kd_vs_avg")
    kills_vs = deltas.get("kills_vs_avg")
    deaths_vs = deltas.get("deaths_vs_avg")

    strengths = []
    weaknesses = []
    recs = []

    if won is True:
        strengths.append({
            "title": "Победа",
            "detail": f"Карта {map_name} · {score}".strip(" ·"),
            "evidence": f"won=true score={score}",
        })
    if kd is not None and kd >= 1.25:
        strengths.append({
            "title": "Сильный K/D",
            "detail": f"K/D {kd:.2f}" + (f" (ср. {avg_kd})" if avg_kd else ""),
            "evidence": f"kd={kd}",
        })
    if kills is not None and avg_kills and kills >= avg_kills + 3:
        strengths.append({
            "title": "Выше среднего по киллам",
            "detail": f"{kills} kills vs ср. {avg_kills}",
            "evidence": f"kills={kills} avg={avg_kills}",
        })
    if mvps is not None and int(mvps) >= 3:
        strengths.append({
            "title": "Много MVP",
            "detail": f"{mvps} MVP в матче",
            "evidence": f"mvps={mvps}",
        })
    if hs is not None:
        try:
            hs_n = float(hs)
            if hs_n >= 40 and (kills is None or hs_n <= 100):
                strengths.append({
                    "title": "Хороший HS",
                    "detail": f"HS {hs}",
                    "evidence": f"hs={hs}",
                })
        except (TypeError, ValueError):
            pass

    if won is False:
        weaknesses.append({
            "title": "Поражение",
            "detail": f"Карта {map_name} · {score}".strip(" ·"),
            "evidence": f"won=false",
        })
    if kd is not None and kd < 0.85:
        weaknesses.append({
            "title": "Низкий K/D",
            "detail": f"K/D {kd:.2f}" + (f", форма {avg_kd}" if avg_kd else ""),
            "evidence": f"kd={kd}",
        })
    if deaths is not None and avg_deaths and deaths >= avg_deaths + 3:
        weaknesses.append({
            "title": "Много смертей",
            "detail": f"{deaths} deaths vs ср. {avg_deaths}",
            "evidence": f"deaths={deaths}",
        })
    if deaths is not None and kills is not None and deaths > kills + 5:
        weaknesses.append({
            "title": "Смерти сильно выше киллов",
            "detail": f"{kills}/{deaths}",
            "evidence": f"k={kills} d={deaths}",
        })
    if kd_vs is not None and kd_vs < -0.25:
        weaknesses.append({
            "title": "Ниже своей формы по K/D",
            "detail": f"Δ K/D {kd_vs:+.2f}",
            "evidence": f"kd_vs_avg={kd_vs}",
        })
    if kills_vs is not None and kills_vs < -3:
        weaknesses.append({
            "title": "Меньше киллов, чем обычно",
            "detail": f"Δ kills {kills_vs:+.1f}",
            "evidence": f"kills_vs_avg={kills_vs}",
        })

    if not strengths and won is None:
        strengths.append({
            "title": "Матч разобран",
            "detail": f"K/D {kd or '—'} · {map_name}",
            "evidence": "fallback",
        })
    if not weaknesses:
        if kd is not None and 0.85 <= kd < 1.1:
            weaknesses.append({
                "title": "Средний K/D",
                "detail": "Есть запас до стабильного плюса",
                "evidence": f"kd={kd}",
            })
        else:
            weaknesses.append({
                "title": "Пока ровно",
                "detail": "Нет явного провала по доступным цифрам",
                "evidence": "none",
            })

    score_n = 50
    if won is True:
        score_n += 12
    elif won is False:
        score_n -= 12
    if kd is not None:
        if kd >= 1.4:
            score_n += 18
        elif kd >= 1.15:
            score_n += 10
        elif kd >= 1.0:
            score_n += 4
        elif kd < 0.7:
            score_n -= 18
        elif kd < 0.9:
            score_n -= 10
    if mvps is not None and int(mvps) >= 3:
        score_n += 6
    if deaths_vs is not None and deaths_vs > 3:
        score_n -= 8
    score_n = max(5, min(95, score_n))

    if deaths is not None and (avg_deaths is None or deaths >= (avg_deaths or 0)):
        recs.append({
            "priority": 1,
            "action": "Срежь лишние смерти: играй ближе к команде в mid-round",
            "why": "Deaths давят K/D и раунды",
        })
    if kd is not None and kd < 1.0:
        recs.append({
            "priority": 2,
            "action": "Не форсируй пики 1vX — бери дуэли с инфой",
            "why": f"K/D {kd:.2f} ниже комфортного",
        })
    if hs is not None:
        try:
            if float(hs) < 35 and (kills or 0) >= 10:
                recs.append({
                    "priority": 3,
                    "action": "DM на headshot-only 10–15 мин перед сессией",
                    "why": "HS% можно поднять",
                })
        except (TypeError, ValueError):
            pass
    if not recs:
        recs.append({
            "priority": 1,
            "action": "Сравни K/D и смерти со средней формой в следующих 5 катках",
            "why": "Нужна стабильность",
        })

    if won is True and kd and kd >= 1.1:
        headline = "Победа с плюсовым K/D"
    elif won is True:
        headline = "Победа, но форма средняя"
    elif won is False and kd and kd >= 1.15:
        headline = "Поражение при хорошей личной статистике"
    elif won is False:
        headline = "Поражение, ниже формы" if (kd_vs or 0) < 0 else "Поражение"
    else:
        headline = "Разбор матча Faceit"

    one_liner = recs[0]["action"] if recs else "Смотри K/D и смерти vs форма"

    return {
        "headline": headline,
        "one_liner": one_liner,
        "score_0_100": score_n,
        "strengths": strengths[:5],
        "weaknesses": weaknesses[:5],
        "recommendations": recs[:4],
        "match_stats": {
            "kills": kills,
            "deaths": deaths,
            "assists": assists,
            "kd": round(kd, 2) if kd is not None else None,
            "headshots": match.get("headshots"),
            "hs_percent": match.get("hs_percent"),
            "mvps": mvps,
            "map": map_name,
            "score": score,
            "won": won,
        },
    }


def analyze_faceit_snapshot(snapshot: dict) -> tuple[dict, str]:
    return _heuristic_faceit(snapshot), "heuristic"
