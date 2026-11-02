"""Country gazetteer, text normalisation and great-circle distance."""

from __future__ import annotations

import math
import re

# country -> (region, aliases). Aliases are matched as whole words, lowercase.
COUNTRIES: dict[str, tuple[str, list[str]]] = {
    "united states": ("north_america", ["united states", "u.s.", "usa", "american", "pentagon", "washington", "white house"]),
    "canada": ("north_america", ["canada", "canadian", "ottawa"]),
    "mexico": ("north_america", ["mexico", "mexican"]),
    "china": ("east_asia", ["china", "chinese", "beijing", "pla"]),
    "taiwan": ("east_asia", ["taiwan", "taiwanese", "taipei"]),
    "japan": ("east_asia", ["japan", "japanese", "tokyo"]),
    "south korea": ("east_asia", ["south korea", "seoul", "south korean"]),
    "north korea": ("east_asia", ["north korea", "pyongyang", "north korean", "dprk"]),
    "philippines": ("southeast_asia", ["philippines", "philippine", "manila"]),
    "vietnam": ("southeast_asia", ["vietnam", "vietnamese"]),
    "thailand": ("southeast_asia", ["thailand", "thai", "bangkok"]),
    "myanmar": ("southeast_asia", ["myanmar", "burma"]),
    "cambodia": ("southeast_asia", ["cambodia", "cambodian"]),
    "indonesia": ("southeast_asia", ["indonesia", "indonesian", "jakarta"]),
    "malaysia": ("southeast_asia", ["malaysia", "malaysian"]),
    "india": ("south_asia", ["india", "indian", "new delhi"]),
    "pakistan": ("south_asia", ["pakistan", "pakistani", "islamabad"]),
    "afghanistan": ("south_asia", ["afghanistan", "afghan", "taliban"]),
    "bangladesh": ("south_asia", ["bangladesh"]),
    "russia": ("europe", ["russia", "russian", "moscow", "kremlin", "putin"]),
    "ukraine": ("europe", ["ukraine", "ukrainian", "kyiv", "kiev", "zelensky"]),
    "belarus": ("europe", ["belarus"]),
    "poland": ("europe", ["poland", "polish", "warsaw"]),
    "germany": ("europe", ["germany", "german", "berlin"]),
    "france": ("europe", ["france", "french", "paris"]),
    "united kingdom": ("europe", ["united kingdom", "britain", "british", "uk", "london"]),
    "baltics": ("europe", ["lithuania", "latvia", "estonia", "baltic"]),
    "serbia": ("europe", ["serbia", "kosovo"]),
    "moldova": ("europe", ["moldova", "transnistria"]),
    "georgia": ("europe", ["tbilisi"]),
    "nato": ("europe", ["nato"]),
    "european union": ("europe", ["european union", "eu", "brussels"]),
    "turkey": ("middle_east", ["turkey", "turkish", "ankara", "turkiye"]),
    "israel": ("middle_east", ["israel", "israeli", "idf", "netanyahu"]),
    "palestine": ("middle_east", ["gaza", "palestinian", "west bank", "hamas"]),
    "lebanon": ("middle_east", ["lebanon", "lebanese", "hezbollah", "beirut"]),
    "syria": ("middle_east", ["syria", "syrian", "damascus"]),
    "iraq": ("middle_east", ["iraq", "iraqi", "baghdad"]),
    "iran": ("middle_east", ["iran", "iranian", "tehran", "irgc"]),
    "saudi arabia": ("middle_east", ["saudi", "riyadh"]),
    "yemen": ("middle_east", ["yemen", "houthi", "houthis"]),
    "qatar": ("middle_east", ["qatar", "doha"]),
    "uae": ("middle_east", ["uae", "emirates", "dubai", "abu dhabi"]),
    "egypt": ("africa", ["egypt", "egyptian", "cairo"]),
    "libya": ("africa", ["libya", "libyan"]),
    "sudan": ("africa", ["sudan", "sudanese", "khartoum", "darfur"]),
    "south sudan": ("africa", ["south sudan"]),
    "ethiopia": ("africa", ["ethiopia", "ethiopian", "tigray"]),
    "somalia": ("africa", ["somalia", "somali", "al-shabab"]),
    "dr congo": ("africa", ["congo", "drc", "kinshasa", "m23"]),
    "nigeria": ("africa", ["nigeria", "nigerian"]),
    "sahel": ("africa", ["mali", "burkina faso", "niger", "sahel", "chad"]),
    "south africa": ("africa", ["south africa"]),
    "venezuela": ("latin_america", ["venezuela", "venezuelan", "caracas", "maduro"]),
    "colombia": ("latin_america", ["colombia", "colombian"]),
    "brazil": ("latin_america", ["brazil", "brazilian"]),
    "argentina": ("latin_america", ["argentina"]),
    "haiti": ("latin_america", ["haiti", "haitian"]),
    "cuba": ("latin_america", ["cuba", "cuban"]),
    "panama": ("latin_america", ["panama"]),
    "australia": ("oceania", ["australia", "australian"]),
}

_ALIAS_RE: list[tuple[re.Pattern, str]] = []
for _country, (_region, _aliases) in COUNTRIES.items():
    for _alias in _aliases:
        _ALIAS_RE.append((re.compile(r"(?<![a-z])" + re.escape(_alias) + r"(?![a-z])"), _country))


def normalize(text: str) -> str:
    text = re.sub(r"<[^>]+>", " ", text or "")
    text = text.replace("’", "'").replace("‘", "'")
    return re.sub(r"\s+", " ", text).strip().lower()


def find_countries(text: str) -> list[str]:
    """Countries mentioned in lowercase text, in order of first appearance."""
    hits: dict[str, int] = {}
    for pattern, country in _ALIAS_RE:
        m = pattern.search(text)
        if m and (country not in hits or m.start() < hits[country]):
            hits[country] = m.start()
    return [c for c, _ in sorted(hits.items(), key=lambda kv: kv[1])]


def region_of(country: str) -> str | None:
    entry = COUNTRIES.get(country)
    return entry[0] if entry else None


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = p2 - p1
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


STOPWORDS = {
    "the", "a", "an", "of", "in", "on", "to", "for", "and", "or", "as", "at", "by", "with",
    "from", "is", "are", "was", "were", "be", "after", "over", "says", "say", "said", "new",
    "amid", "into", "its", "his", "her", "their", "has", "have", "will", "not", "but", "this",
    "that", "it", "live", "update", "updates", "video", "watch",
}


def title_tokens(text: str) -> set[str]:
    return {t for t in re.findall(r"[a-z][a-z0-9\-']+", text) if t not in STOPWORDS and len(t) > 2}


COUNTRY_TH = {
    "united states": "สหรัฐฯ", "canada": "แคนาดา", "mexico": "เม็กซิโก", "china": "จีน",
    "taiwan": "ไต้หวัน", "japan": "ญี่ปุ่น", "south korea": "เกาหลีใต้", "north korea": "เกาหลีเหนือ",
    "philippines": "ฟิลิปปินส์", "vietnam": "เวียดนาม", "thailand": "ไทย", "myanmar": "เมียนมา",
    "cambodia": "กัมพูชา", "indonesia": "อินโดนีเซีย", "malaysia": "มาเลเซีย", "india": "อินเดีย",
    "pakistan": "ปากีสถาน", "afghanistan": "อัฟกานิสถาน", "bangladesh": "บังกลาเทศ",
    "russia": "รัสเซีย", "ukraine": "ยูเครน", "belarus": "เบลารุส", "poland": "โปแลนด์",
    "germany": "เยอรมนี", "france": "ฝรั่งเศส", "united kingdom": "สหราชอาณาจักร",
    "baltics": "กลุ่มประเทศบอลติก", "serbia": "เซอร์เบีย/โคโซโว", "moldova": "มอลโดวา",
    "georgia": "จอร์เจีย", "nato": "นาโต", "european union": "สหภาพยุโรป", "turkey": "ตุรกี",
    "israel": "อิสราเอล", "palestine": "ปาเลสไตน์/กาซา", "lebanon": "เลบานอน", "syria": "ซีเรีย",
    "iraq": "อิรัก", "iran": "อิหร่าน", "saudi arabia": "ซาอุดีอาระเบีย", "yemen": "เยเมน",
    "qatar": "กาตาร์", "uae": "สหรัฐอาหรับเอมิเรตส์", "egypt": "อียิปต์", "libya": "ลิเบีย",
    "sudan": "ซูดาน", "south sudan": "ซูดานใต้", "ethiopia": "เอธิโอเปีย", "somalia": "โซมาเลีย",
    "dr congo": "คองโก", "nigeria": "ไนจีเรีย", "sahel": "ภูมิภาคซาเฮล", "south africa": "แอฟริกาใต้",
    "venezuela": "เวเนซุเอลา", "colombia": "โคลอมเบีย", "brazil": "บราซิล", "argentina": "อาร์เจนตินา",
    "haiti": "เฮติ", "cuba": "คิวบา", "panama": "ปานามา", "australia": "ออสเตรเลีย",
}


def countries_th(countries: list[str], limit: int = 3) -> str:
    names = [COUNTRY_TH.get(c, c.title()) for c in countries[:limit]]
    return "–".join(names) if names else "หลายพื้นที่"


COUNTRY_EN_OVERRIDE = {"united states": "US", "united kingdom": "UK", "uae": "UAE", "dr congo": "DR Congo",
                       "nato": "NATO", "european union": "EU", "palestine": "Palestine/Gaza", "baltics": "Baltic states"}


def countries_en(countries: list[str], limit: int = 3) -> str:
    names = [COUNTRY_EN_OVERRIDE.get(c, c.title()) for c in countries[:limit]]
    return "–".join(names) if names else "multiple areas"
