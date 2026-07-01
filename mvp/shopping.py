# -*- coding: utf-8 -*-
"""Подбор образов со ссылками на Wildberries (поисковые deep-links, без API)."""

import urllib.parse

WB_SEARCH = "https://www.wildberries.ru/catalog/0/search.aspx?search="

# Конкретные вещи под каждое семейство Кибби (шоппинг-запросы).
KIBBE_ITEMS = {
    "Dramatic": ["пальто прямое длинное", "брюки со стрелками", "платье-футляр", "жакет структурный"],
    "Natural": ["пальто оверсайз", "джинсы прямые", "джемпер крупной вязки", "рубашка свободная"],
    "Classic": ["жакет классический", "юбка-карандаш", "рубашка шёлковая", "брюки прямые"],
    "Gamine": ["жакет укороченный", "джинсы зауженные", "тельняшка", "юбка мини трапеция"],
    "Romantic": ["платье с запахом", "юбка миди плиссе", "блузка с драпировкой", "кардиган мягкий"],
}


def wb_link(query):
    return WB_SEARCH + urllib.parse.quote(query)


def outfit_links(kibbe_family, color_word, limit=3):
    """Возвращает [{label, url}] — вещи под типаж, с цветом-подсказкой."""
    items = KIBBE_ITEMS.get(kibbe_family, KIBBE_ITEMS["Classic"])
    out = []
    for it in items[:limit]:
        query = ("%s %s" % (color_word, it)).strip()
        out.append({"label": it, "query": query, "url": wb_link(query)})
    return out


if __name__ == "__main__":
    for l in outfit_links("Dramatic", "тёмно-синий"):
        print(l["label"], "->", l["url"])
