# -*- coding: utf-8 -*-
"""
Стилист — движок анализа (MVP).
Без внешних зависимостей. Python 3.9+.

Главная функция:
    analyze_profile(answers: dict, vision: dict | None = None) -> dict

answers — словарь {question_id: option_id} из опросника (см. QUESTIONS).
vision  — опционально параметры от фото-модели: undertone/value/chroma/contrast/lean.

Запуск самопроверки:  python engine.py --selftest
"""

import json
import os
import sys

import colors
import shopping

BASE = os.path.dirname(os.path.abspath(__file__))
KB_DIR = os.path.join(BASE, "kb")


# ---------------------------------------------------------------- база знаний
def _load(name):
    path = os.path.join(KB_DIR, name)
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _validate_kb(kibbe, seasons, archetypes):
    assert len(kibbe["types"]) == 13, "Kibbe: ожидается 13 типов"
    assert len(seasons["seasons"]) == 12, "Seasons: ожидается 12 сезонов"
    assert len(archetypes["archetypes"]) == 7, "Archetypes: ожидается 7 архетипов"
    for t in kibbe["types"]:
        for k in ("id", "name", "family", "line", "recommendations", "avoid"):
            assert k in t, "Kibbe '%s': нет поля %s" % (t.get("id"), k)
    for s in seasons["seasons"]:
        for k in ("id", "name", "undertone", "value", "chroma", "palette"):
            assert k in s, "Season '%s': нет поля %s" % (s.get("id"), k)
    for a in archetypes["archetypes"]:
        for k in ("id", "name", "description"):
            assert k in a, "Archetype '%s': нет поля %s" % (a.get("id"), k)


KIBBE = _load("kibbe.json")
SEASONS = _load("seasons.json")
ARCHETYPES = _load("archetypes.json")
_validate_kb(KIBBE, SEASONS, ARCHETYPES)

KIBBE_BY_ID = {t["id"]: t for t in KIBBE["types"]}
SEASON_BY_ID = {s["id"]: s for s in SEASONS["seasons"]}
ARCH_BY_ID = {a["id"]: a for a in ARCHETYPES["archetypes"]}


# ---------------------------------------------------------------- опросник
# Структура отдаётся клиенту через API /questions; bot строит из неё кнопки.
QUESTIONS = [
    {"id": "q_height", "text": "Какой у вас рост?",
     "options": [{"id": "short", "label": "До 160 см"},
                 {"id": "mid", "label": "160–172 см"},
                 {"id": "tall", "label": "Выше 172 см"}]},
    {"id": "q_bone", "text": "Костяк и плечи — какие?",
     "options": [{"id": "sharp", "label": "Острые, выраженные кости"},
                 {"id": "broad", "label": "Широкие, крупные"},
                 {"id": "soft", "label": "Мягкие, узкие/округлые"}]},
    {"id": "q_face", "text": "Черты лица по ощущению?",
     "options": [{"id": "sharp", "label": "Резкие, графичные"},
                 {"id": "balanced", "label": "Сбалансированные"},
                 {"id": "soft", "label": "Мягкие, округлые"}]},
    {"id": "q_flesh", "text": "Телосложение (плоть тела)?",
     "options": [{"id": "lean", "label": "Поджарое, жилистое"},
                 {"id": "moderate", "label": "Умеренное"},
                 {"id": "soft", "label": "Мягкое, пышное"}]},
    {"id": "q_fit", "text": "Как на вас лучше сидит одежда?",
     "options": [{"id": "straight", "label": "Прямые вещи смотрятся лучше"},
                 {"id": "balanced", "label": "По-разному, нужен баланс"},
                 {"id": "waist", "label": "Хочется подчеркнуть талию"}]},
    {"id": "q_proportion", "text": "Общее впечатление от фигуры?",
     "options": [{"id": "compact", "label": "Компактная, черты контрастные"},
                 {"id": "even", "label": "Ровная, средняя"},
                 {"id": "elongated", "label": "Вытянутая, цельная"}]},
    {"id": "q_undertone", "text": "Подтон: вены на запястье / какой металл идёт?",
     "options": [{"id": "cool", "label": "Голубые вены / серебро"},
                 {"id": "warm", "label": "Зеленоватые вены / золото"},
                 {"id": "neutral", "label": "И то и другое"}]},
    {"id": "q_value", "text": "Общая глубина внешности?",
     "options": [{"id": "light", "label": "Светлая (светлые волосы/глаза)"},
                 {"id": "medium", "label": "Средняя"},
                 {"id": "deep", "label": "Глубокая (тёмные волосы/глаза)"}]},
    {"id": "q_chroma", "text": "Какие цвета вас оживляют?",
     "options": [{"id": "bright", "label": "Яркие, чистые"},
                 {"id": "medium", "label": "Средние"},
                 {"id": "soft", "label": "Приглушённые, мягкие"}]},
    {"id": "q_contrast", "text": "Контраст волос / кожи / глаз?",
     "options": [{"id": "high", "label": "Высокий"},
                 {"id": "medium", "label": "Средний"},
                 {"id": "low", "label": "Низкий"}]},
    {"id": "q_arch1", "text": "Какой образ вам ближе?",
     "options": [{"id": "classic", "label": "Строгий костюм, чистые линии"},
                 {"id": "romantic", "label": "Платье, мягкие ткани, женственно"},
                 {"id": "natural", "label": "Джинсы, свитер, комфорт"},
                 {"id": "dramatic", "label": "Смелый акцентный образ"}]},
    {"id": "q_arch2", "text": "А ещё ближе что?",
     "options": [{"id": "elegant_chic", "label": "Минимализм, дорогая простота"},
                 {"id": "creative", "label": "Яркие цвета, необычные сочетания"},
                 {"id": "edgy", "label": "Кожа, чёрный, металл, дерзко"},
                 {"id": "natural", "label": "Уютный многослойный кэжуал"}]},
]
QUESTION_IDS = [q["id"] for q in QUESTIONS]


# ---------------------------------------------------------------- скоринг Кибби
# Каждая (вопрос, ответ) даёт очки семействам (fam_*) и шкале инь/ян.
KIBBE_SCORING = {
    "q_height": {
        "short": {"fam_G": 2, "fam_R": 1, "yin": 1},
        "mid": {"fam_C": 1},
        "tall": {"fam_D": 2, "fam_N": 1, "yang": 1},
    },
    "q_bone": {
        "sharp": {"fam_D": 2, "yang": 2},
        "broad": {"fam_N": 2, "yang": 1},
        "soft": {"fam_R": 2, "fam_G": 1, "yin": 2},
    },
    "q_face": {
        "sharp": {"fam_D": 2, "yang": 1},
        "balanced": {"fam_C": 2},
        "soft": {"fam_R": 2, "yin": 1},
    },
    "q_flesh": {
        "lean": {"fam_D": 1, "fam_N": 1, "yang": 1},
        "moderate": {"fam_C": 1},
        "soft": {"fam_R": 2, "yin": 2},
    },
    "q_fit": {
        "straight": {"fam_D": 1, "fam_N": 1, "yang": 1},
        "balanced": {"fam_C": 1, "fam_G": 1},
        "waist": {"fam_R": 1, "fam_G": 1, "yin": 1},
    },
    "q_proportion": {
        "compact": {"fam_G": 3},
        "even": {"fam_C": 1},
        "elongated": {"fam_D": 1, "fam_N": 1, "yang": 1},
    },
}

FAMILY_NAMES = {"D": "Dramatic", "N": "Natural", "C": "Classic",
                "G": "Gamine", "R": "Romantic"}

# Подтипы по семействам. lean = yin - yang (положительный = мягче).
FAMILY_SUBTYPES = {
    "D": {"soft": "soft_dramatic", "mid": "dramatic", "yang": "dramatic"},
    "N": {"soft": "soft_natural", "mid": "natural", "yang": "flamboyant_natural"},
    "C": {"soft": "soft_classic", "mid": "classic", "yang": "dramatic_classic"},
    "G": {"soft": "soft_gamine", "mid": "gamine", "yang": "flamboyant_gamine"},
    "R": {"soft": "romantic", "mid": "romantic", "yang": "theatrical_romantic"},
}


def _score_kibbe(answers):
    fam = {"fam_D": 0, "fam_N": 0, "fam_C": 0, "fam_G": 0, "fam_R": 0}
    yang = yin = 0
    answered = 0
    for q, table in KIBBE_SCORING.items():
        opt = answers.get(q)
        if opt is None or opt not in table:
            continue
        answered += 1
        for key, val in table[opt].items():
            if key == "yang":
                yang += val
            elif key == "yin":
                yin += val
            else:
                fam[key] += val
    return fam, yang, yin, answered


def _pick_kibbe(answers, vision):
    fam, yang, yin, answered = _score_kibbe(answers)
    # ранжируем семейства
    ranked = sorted(fam.items(), key=lambda kv: kv[1], reverse=True)
    top_key = ranked[0][0][-1]  # 'D'/'N'/'C'/'G'/'R'
    top_val = ranked[0][1]
    second_val = ranked[1][1] if len(ranked) > 1 else 0

    lean = yin - yang
    if vision and isinstance(vision.get("lean"), (int, float)):
        lean += vision["lean"]

    sub = FAMILY_SUBTYPES[top_key]
    if lean >= 2:
        type_id = sub["soft"]
    elif lean <= -2:
        type_id = sub["yang"]
    else:
        type_id = sub["mid"]

    # уверенность: отрыв лидера + полнота ответов
    margin = top_val - second_val
    conf = 0.55 + 0.07 * margin
    if answered < len(KIBBE_SCORING):
        conf -= 0.05 * (len(KIBBE_SCORING) - answered)
    conf = max(0.4, min(0.9, conf))

    t = KIBBE_BY_ID[type_id]
    return {
        "id": t["id"], "name": t["name"], "family": t["family"],
        "line": t["line"], "confidence": round(conf, 2),
        "recommendations": t["recommendations"], "avoid": t["avoid"],
    }


# ---------------------------------------------------------------- скоринг цвета
def _pick_season(answers, vision):
    v_in = vision or {}
    u = v_in.get("undertone") or answers.get("q_undertone", "neutral")
    val = v_in.get("value") or answers.get("q_value", "medium")
    c = v_in.get("chroma") or answers.get("q_chroma", "medium")
    contrast = v_in.get("contrast") or answers.get("q_contrast", "medium")

    if u == "warm":
        spring = (val == "light") + (c == "bright")
        autumn = (val == "deep") + (c == "soft")
        if spring >= autumn:
            sid = "bright_spring" if c == "bright" else ("light_spring" if val == "light" else "warm_spring")
        else:
            sid = "deep_autumn" if val == "deep" else ("soft_autumn" if c == "soft" else "warm_autumn")
    elif u == "cool":
        winter = (val == "deep") + (c == "bright") + (contrast == "high")
        summer = (val == "light") + (c == "soft") + (contrast == "low")
        if winter >= summer:
            sid = "deep_winter" if val == "deep" else ("bright_winter" if c == "bright" else "cool_winter")
        else:
            sid = "light_summer" if val == "light" else ("soft_summer" if c == "soft" else "cool_summer")
    else:  # neutral
        if val == "light":
            sid = "light_summer"
        elif val == "deep":
            sid = "deep_winter" if c == "bright" else "deep_autumn"
        else:
            sid = "bright_winter" if c == "bright" else ("soft_summer" if c == "soft" else "soft_autumn")

    # уверенность: сколько осей дали определённый (не средний) сигнал
    decisive = sum([u in ("warm", "cool"), val in ("light", "deep"),
                    c in ("bright", "soft"), contrast in ("high", "low")])
    conf = round(min(0.95, 0.55 + 0.1 * decisive), 2)

    s = SEASON_BY_ID[sid]
    out = dict(s)
    out["confidence"] = conf
    return out


# ---------------------------------------------------------------- архетип
ARCH_SCORING = {
    "q_arch1": {
        "classic": {"classic": 2, "elegant_chic": 1},
        "romantic": {"romantic": 2},
        "natural": {"natural": 2},
        "dramatic": {"dramatic": 2},
    },
    "q_arch2": {
        "elegant_chic": {"elegant_chic": 2, "classic": 1},
        "creative": {"creative": 2},
        "edgy": {"edgy": 2},
        "natural": {"natural": 2, "creative": 1},
    },
}


def _pick_archetype(answers):
    score = {a["id"]: 0 for a in ARCHETYPES["archetypes"]}
    for q, table in ARCH_SCORING.items():
        opt = answers.get(q)
        if opt and opt in table:
            for aid, val in table[opt].items():
                score[aid] += val
    ranked = sorted(score.items(), key=lambda kv: kv[1], reverse=True)
    primary = ranked[0][0]
    secondary = ranked[1][0] if ranked[1][1] > 0 else None
    names = [ARCH_BY_ID[primary]["name"]]
    if secondary:
        names.append(ARCH_BY_ID[secondary]["name"])
    return {
        "primary": primary, "secondary": secondary, "names": names,
        "description": ARCH_BY_ID[primary]["description"],
        "signature": ARCH_BY_ID[primary]["signature"],
    }


# ---------------------------------------------------------------- сборка профиля
def analyze_profile(answers, vision=None):
    answers = answers or {}
    kibbe = _pick_kibbe(answers, vision)
    season = _pick_season(answers, vision)
    arch = _pick_archetype(answers)

    rec = kibbe["recommendations"]
    palette_named = [{"hex": h, "name": colors.name_ru(h), "role": colors.role_ru(h)}
                     for h in season["palette"]]
    # базовый цвет-подсказка для шоппинга — тёмная нейтраль сезона
    neutrals = season.get("neutrals", [])
    base_word = colors.name_ru(neutrals[-1]) if neutrals else colors.name_ru(season["palette"][0])
    recommendations = {
        "palette": season["palette"],
        "palette_named": palette_named,
        "neutrals": neutrals,
        "silhouettes": rec.get("silhouettes", []),
        "fabrics": rec.get("fabrics", []),
        "necklines": rec.get("necklines", []),
        "accessories": rec.get("accessories", []),
        "metals": season.get("metals", []),
        "capsule": _capsule(kibbe, arch),
        "shopping": shopping.outfit_links(kibbe["family"], base_word),
        "avoid": list(kibbe.get("avoid", [])) + list(season.get("avoid", [])),
    }

    summary = _summary(kibbe, season, arch)
    return {
        "kibbe": kibbe,
        "season": season,
        "archetype": arch,
        "recommendations": recommendations,
        "summary": summary,
        "disclaimer": "Типаж по Кибби и архетип — это гипотеза с уровнем уверенности. "
                      "Вы можете скорректировать результат, и рекомендации обновятся.",
    }


def _capsule(kibbe, arch):
    base = list(kibbe["recommendations"].get("silhouettes", []))[:2]
    sig = list(arch.get("signature", []))[:2]
    return base + sig


def _summary(kibbe, season, arch):
    arch_str = " + ".join(arch["names"])
    palette_preview = ", ".join(season["palette"][:4])
    return (
        "Ваш типаж по Кибби — %s (семейство %s, уверенность %d%%). "
        "Цветотип — %s (%d%%): ваши цвета — %s. "
        "Стилевая личность: %s. "
        "Опирайтесь на эту базу: %s. Избегайте: %s."
        % (
            kibbe["name"], kibbe["family"], int(kibbe["confidence"] * 100),
            season["name"], int(season["confidence"] * 100), palette_preview,
            arch_str,
            (kibbe["recommendations"].get("silhouettes") or ["—"])[0].lower(),
            (kibbe.get("avoid") or ["—"])[0].lower(),
        )
    )


# ---------------------------------------------------------------- self-test
def _selftest():
    cases = [
        ("Чистый ян, высокая, тёмная, яркая",
         {"q_height": "tall", "q_bone": "sharp", "q_face": "sharp", "q_flesh": "lean",
          "q_fit": "straight", "q_proportion": "elongated", "q_undertone": "cool",
          "q_value": "deep", "q_chroma": "bright", "q_contrast": "high",
          "q_arch1": "dramatic", "q_arch2": "edgy"},
         "Dramatic"),
        ("Чистый инь, низкая, тёплая мягкая",
         {"q_height": "short", "q_bone": "soft", "q_face": "soft", "q_flesh": "soft",
          "q_fit": "waist", "q_proportion": "even", "q_undertone": "warm",
          "q_value": "medium", "q_chroma": "soft", "q_contrast": "low",
          "q_arch1": "romantic", "q_arch2": "creative"},
         "Romantic"),
        ("Натурал: высокая, широкий костяк",
         {"q_height": "tall", "q_bone": "broad", "q_face": "balanced", "q_flesh": "lean",
          "q_fit": "straight", "q_proportion": "elongated", "q_undertone": "warm",
          "q_value": "medium", "q_chroma": "soft", "q_contrast": "low",
          "q_arch1": "natural", "q_arch2": "natural"},
         "Natural"),
        ("Классик: всё сбалансировано",
         {"q_height": "mid", "q_bone": "broad", "q_face": "balanced", "q_flesh": "moderate",
          "q_fit": "balanced", "q_proportion": "even", "q_undertone": "neutral",
          "q_value": "medium", "q_chroma": "medium", "q_contrast": "medium",
          "q_arch1": "classic", "q_arch2": "elegant_chic"},
         "Classic"),
        ("Гамин: низкая, контрастная",
         {"q_height": "short", "q_bone": "sharp", "q_face": "balanced", "q_flesh": "moderate",
          "q_fit": "balanced", "q_proportion": "compact", "q_undertone": "cool",
          "q_value": "medium", "q_chroma": "bright", "q_contrast": "high",
          "q_arch1": "dramatic", "q_arch2": "creative"},
         "Gamine"),
        ("Пустые ответы (дефолты не должны ронять)",
         {}, None),
    ]
    ok = True
    for title, ans, expect_family in cases:
        try:
            p = analyze_profile(ans)
            fam = p["kibbe"]["family"]
            mark = "OK"
            if expect_family and fam != expect_family:
                mark = "ОЖИДАЛОСЬ %s, ПОЛУЧЕНО %s" % (expect_family, fam)
                ok = False
            print("[%s] %s" % (mark, title))
            print("    Кибби : %s (%s, %.0f%%)" % (
                p["kibbe"]["name"], fam, p["kibbe"]["confidence"] * 100))
            print("    Сезон : %s (%.0f%%), палитра %d цветов" % (
                p["season"]["name"], p["season"]["confidence"] * 100,
                len(p["season"]["palette"])))
            print("    Архетип: %s" % " + ".join(p["archetype"]["names"]))
            print("")
        except Exception as e:  # noqa
            ok = False
            print("[ОШИБКА] %s -> %s" % (title, e))
    print("ИТОГ:", "ВСЕ ПРОВЕРКИ ПРОЙДЕНЫ" if ok else "ЕСТЬ РАСХОЖДЕНИЯ")
    return ok


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        sys.exit(0 if _selftest() else 1)
    else:
        # демо
        demo = {"q_height": "tall", "q_bone": "sharp", "q_face": "sharp",
                "q_flesh": "lean", "q_fit": "straight", "q_proportion": "elongated",
                "q_undertone": "cool", "q_value": "deep", "q_chroma": "bright",
                "q_contrast": "high", "q_arch1": "dramatic", "q_arch2": "edgy"}
        print(json.dumps(analyze_profile(demo), ensure_ascii=False, indent=2))
