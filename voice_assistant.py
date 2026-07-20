# ── VOICE ASSISTANT MODULE ───────────────────────────────────────────────────
# Functions exported:
#   parse_voice_command(text)      — main entry (AI + keyword fallback)
#   generate_recipe_idea(item, lang)
#   extract_purchase_date(text)
#   extract_expiry_date(text)
#   detect_category(name)
# ─────────────────────────────────────────────────────────────────────────────

import os, re, json
from datetime import date, timedelta
from google import genai
from google.genai import types

# ── AI CLIENT (Google Gemini) ──────────────────────────────────────────────────
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
ai_client = genai.Client(api_key=GEMINI_API_KEY) if GEMINI_API_KEY else None
GEMINI_MODEL = "gemini-2.5-flash"

# ── MONTH MAP ─────────────────────────────────────────────────────────────────
MONTH_MAP = {
    "january":1,"february":2,"march":3,"april":4,"may":5,"june":6,
    "july":7,"august":8,"september":9,"october":10,"november":11,"december":12,
    "jan":1,"feb":2,"mar":3,"apr":4,"jun":6,"jul":7,"aug":8,
    "sep":9,"oct":10,"nov":11,"dec":12,
    "जनवरी":1,"फरवरी":2,"मार्च":3,"अप्रैल":4,"मई":5,"जून":6,
    "जुलाई":7,"अगस्त":8,"सितंबर":9,"अक्टूबर":10,"नवंबर":11,"दिसंबर":12,
}
_MONTH_ALT = "|".join(sorted(MONTH_MAP.keys(), key=len, reverse=True))
_NAMED_DATE_PAT = re.compile(
    rf'(\d{{1,2}})\s*(?:st|nd|rd|th)?\s+({_MONTH_ALT})\s+(\d{{4}})',
    re.IGNORECASE
)

# ── CATEGORY KEYWORDS ────────────────────────────────────────────────────────
CATEGORY_KEYWORDS = {
    "Cosmetics": [
        "moisturizer","lotion","sunscreen","face wash","toner","serum","scrub",
        "lipstick","lip gloss","foundation","concealer","mascara","kajal",
        "eyeliner","eyeshadow","shampoo","conditioner","hair oil","body wash",
        "soap","deodorant","perfume","nail polish",
        "मॉइस्चराइज़र","लोशन","सनस्क्रीन","शैम्पू","साबुन","परफ्यूम","काजल","लिपस्टिक","क्रीम",
    ],
    "Medicine": [
        "tablet","capsule","syrup","ointment","medicine","dawa",
        "दवा","टैबलेट","कैप्सूल","सिरप","गोली",
    ],
    "Jewelry": [
        "earring","necklace","ring","bangle","chain","bracelet","jewelry","jewellery",
        "silver","gold","platinum",
        "अंगूठी","झुमका","हार","चूड़ी","सोना","चांदी","ज्वेलरी","बाली",
    ],
    "Groceries": [
        "rice","chawal","flour","atta","maida","oil","tel","ghee","sugar","cheeni",
        "dal","noodles","maggi","pasta","biscuit","chocolate","chips","sauce",
        "ketchup","pickle","achar","jam","honey","shehad","tea","coffee","oats",
        "namkeen","chhola masala","chhole masala","pav bhaji masala","masala",
        "चावल","आटा","मैदा","तेल","घी","चीनी","दाल","नूडल्स","बिस्कुट","चॉकलेट",
        "चिप्स","अचार","शहद","चाय","कॉफ़ी","कॉफी",
        "नमकीन","छोला मसाला","छोले मसाला","पाव भाजी मसाला","मसाला",
    ],
    "Food": [
        "milk","doodh","dudh","cream","butter","cheese","paneer","yogurt","dahi",
        "curd","bread","pav","roti","egg","anda","chicken","mutton","tomato",
        "tamatar","onion","pyaz","potato","aloo","carrot","gajar","spinach",
        "palak","cabbage","capsicum","broccoli","apple","seb","banana","kela",
        "mango","aam","orange","grapes","papaya","juice",
        "दूध","दही","पनीर","ब्रेड","रोटी","अंडा","चिकन","मटन","टमाटर","प्याज़","प्याज",
        "आलू","गाजर","पालक","सेब","केला","आम","संतरा","अंगूर","मक्खन","पाव",
    ],
}

# ── NUMBER WORDS ──────────────────────────────────────────────────────────────
NUMBER_WORDS = {
    "one":1,"two":2,"three":3,"four":4,"five":5,
    "six":6,"seven":7,"eight":8,"nine":9,"ten":10,
    "ek":1,"do":2,"teen":3,"tin":3,"char":4,"chaar":4,
    "paanch":5,"panch":5,"chhe":6,"che":6,"saat":7,
    "aath":8,"nau":9,"das":10,
    "एक":1,"दो":2,"तीन":3,"चार":4,"पांच":5,"पाँच":5,
    "छह":6,"छः":6,"सात":7,"आठ":8,"नौ":9,"दस":10,
}
_NW_ALT = "|".join(sorted(NUMBER_WORDS.keys(), key=len, reverse=True))
NUMBER_PATTERN = rf'(\d+|{_NW_ALT})'


def _word_to_number(w):
    if w.isdigit(): return int(w)
    return NUMBER_WORDS.get(w.lower())


def _find_all_named_dates(text):
    """Return list of (date_str YYYY-MM-DD, match_object) for all 'DD Month YYYY' in text."""
    results = []
    for m in _NAMED_DATE_PAT.finditer(text):
        day = int(m.group(1))
        month = MONTH_MAP.get(m.group(2).lower()) or MONTH_MAP.get(m.group(2))
        year = int(m.group(3))
        if month:
            try:
                d = date(year, month, day).strftime("%Y-%m-%d")
                results.append((d, m))
            except Exception:
                pass
    return results


# ── PUBLIC: detect_category ───────────────────────────────────────────────────
def detect_category(name):
    if not name: return None
    nl = name.lower()
    for cat, words in CATEGORY_KEYWORDS.items():
        for w in words:
            if w in nl:
                return cat
    return None


# ── PUBLIC: extract_purchase_date ─────────────────────────────────────────────
def extract_purchase_date(text):
    """
    Spoken text se purchase date nikalo.
    - Agar 2 named dates hain → pehli = purchase
    - Agar 1 named date hai aur expiry keyword NAHI → purchase
    - Agar 1 named date hai aur expiry keyword BHI → purchase nahi (woh expiry hai)
    - Relative phrases: aaj, kal, parso, X din pehle, pichle hafte
    """
    t = text.lower()
    today = date.today()

    expiry_kw = ["expire","expiry","kharab","एक्सपायर","ख़राब","खराब",
                 "tak chalega","best before","use by"]

    named = _find_all_named_dates(t)
    if len(named) >= 2:
        return named[0][0]   # pehli date = purchase
    if len(named) == 1:
        has_expiry_kw = any(w in t for w in expiry_kw)
        if not has_expiry_kw:
            return named[0][0]  # sirf purchase date hai
        # Agar expiry keyword hai to check karo — kya "liya/kharida" phrase pehle aata hai
        purchase_kw = ["liya","kharida","kharidi","liye","bought","purchased",
                       "लिया","खरीदा","खरीदी"]
        if any(w in t for w in purchase_kw):
            return named[0][0]  # purchase date + expiry date dono, named[0] purchase

    # Relative dates
    m = re.search(NUMBER_PATTERN + r'\s*(din|days?|दिन)\s*(pehle|pahle|ago|पहले)', t)
    if m:
        n = _word_to_number(m.group(1))
        if n: return (today - timedelta(days=n)).strftime("%Y-%m-%d")

    m = re.search(NUMBER_PATTERN + r'\s*(hafte|hafta|hafton|weeks?|हफ्त[ाोें])\s*(pehle|pahle|ago|पहले)', t)
    if m:
        n = _word_to_number(m.group(1))
        if n: return (today - timedelta(weeks=n)).strftime("%Y-%m-%d")

    if any(w in t for w in ["parso","परसों","day before yesterday"]):
        return (today - timedelta(days=2)).strftime("%Y-%m-%d")
    if any(w in t for w in ["pichhle hafte","pichle hafte","last week","पिछले हफ्ते","पिछले सप्ताह"]):
        return (today - timedelta(weeks=1)).strftime("%Y-%m-%d")
    if any(w in t for w in ["kal","yesterday","कल"]):
        return (today - timedelta(days=1)).strftime("%Y-%m-%d")
    if any(w in t for w in ["aaj","today","आज"]):
        return today.strftime("%Y-%m-%d")

    return None


# ── PUBLIC: extract_expiry_date ───────────────────────────────────────────────
def extract_expiry_date(text):
    """
    Spoken text se expiry date nikalo.
    - 2 named dates → doosri = expiry
    - 1 named date + expiry keyword → woh = expiry
    - Relative: X din/hafte/mahine/saal mein, agle hafte, etc.
    - Explicit ISO / DD-MM-YYYY
    """
    t = text.lower()
    today = date.today()

    expiry_kw = ["expire","expiry","kharab","एक्सपायर","ख़राब","खराब",
                 "tak chalega","tak theek","best before","use by"]

    named = _find_all_named_dates(t)
    if len(named) >= 2:
        return named[1][0]   # doosri date = expiry
    if len(named) == 1:
        if any(w in t for w in expiry_kw):
            return named[0][0]

    # Explicit ISO: 2025-06-15
    m = re.search(r'(\d{4})-(\d{2})-(\d{2})', t)
    if m:
        try: return date(int(m.group(1)),int(m.group(2)),int(m.group(3))).strftime("%Y-%m-%d")
        except: pass

    # Explicit DD/MM/YYYY
    m = re.search(r'(\d{1,2})[/\-](\d{1,2})[/\-](\d{4})', t)
    if m:
        try: return date(int(m.group(3)),int(m.group(2)),int(m.group(1))).strftime("%Y-%m-%d")
        except: pass

    # X din mein/baad
    m = re.search(NUMBER_PATTERN + r'\s*(din|days?|दिन)\s*(mein|me|baad|बाद|में)', t)
    if m:
        n = _word_to_number(m.group(1))
        if n: return (today + timedelta(days=n)).strftime("%Y-%m-%d")

    # X hafte mein/baad
    m = re.search(NUMBER_PATTERN + r'\s*(hafte|hafta|weeks?|हफ्त[ाोें])\s*(mein|me|baad|बाद|में)', t)
    if m:
        n = _word_to_number(m.group(1))
        if n: return (today + timedelta(weeks=n)).strftime("%Y-%m-%d")

    # X mahine mein/baad
    m = re.search(NUMBER_PATTERN + r'\s*(mahine?|mahina|months?|महीने?|माह)\s*(mein|me|baad|बाद|में)?', t)
    if m:
        n = _word_to_number(m.group(1))
        if n: return (today + timedelta(days=n*30)).strftime("%Y-%m-%d")

    # X saal mein/baad
    m = re.search(NUMBER_PATTERN + r'\s*(saal|years?|साल|वर्ष)\s*(mein|me|baad|बाद|में)?', t)
    if m:
        n = _word_to_number(m.group(1))
        if n: return (today + timedelta(days=n*365)).strftime("%Y-%m-%d")

    if any(w in t for w in ["kal expire","kal kharab","tomorrow expire","kal tak"]):
        return (today + timedelta(days=1)).strftime("%Y-%m-%d")
    if any(w in t for w in ["agle hafte","agli hafte","next week","अगले हफ्ते","अगले सप्ताह"]):
        return (today + timedelta(weeks=1)).strftime("%Y-%m-%d")
    if any(w in t for w in ["agle mahine","agli mahine","next month","अगले महीने"]):
        return (today + timedelta(days=30)).strftime("%Y-%m-%d")

    return None


# ── PRIVATE: clean item name from raw text ────────────────────────────────────
def _extract_item_name(text):
    """
    Raw spoken text se sirf item name nikalo.
    Step 1: saari date phrases regex se hatao
    Step 2: command/filler words hatao
    Step 3: CATEGORY_KEYWORDS se match karo → cleanest possible name
    """
    t = text.lower()

    # Step 1: named date patterns hatao (e.g. "24 june 2026")
    t = _NAMED_DATE_PAT.sub(" ", t)

    # Step 2: date-relative patterns hatao
    date_patterns = [
        rf'{NUMBER_PATTERN}\s*(st|nd|rd|th)',           # ordinals: 12th, 3rd
        rf'{NUMBER_PATTERN}\s*(din|days?|दिन)\s*(pehle|pahle|ago|पहले)',
        rf'{NUMBER_PATTERN}\s*(hafte|hafta|weeks?|हफ्त[ाोें])\s*(pehle|pahle|ago|पहले)',
        rf'{NUMBER_PATTERN}\s*(din|days?|दिन)\s*(mein|me|baad|बाद|में)',
        rf'{NUMBER_PATTERN}\s*(hafte|hafta|weeks?|हफ्त[ाोें])\s*(mein|me|baad|बाद|में)',
        rf'{NUMBER_PATTERN}\s*(mahine?|mahina|months?|महीने?|माह)\s*(mein|me|baad|बाद|में)?',
        rf'{NUMBER_PATTERN}\s*(saal|years?|साल|वर्ष)\s*(mein|me|baad|बाद|में)?',
        r'\d{4}-\d{2}-\d{2}',
        r'\d{1,2}[/\-]\d{1,2}[/\-]\d{4}',
    ]
    for pat in date_patterns:
        t = re.sub(pat, " ", t)

    # Step 3: filler/command words hatao
    strip_words = [
        # commands
        "please","add","jodo","jodein","karo","kar do","daalo","dalo",
        "naya item","naya","item",
        "जोड़ो","जोड़ें","डालो","ऐड","एड करो","करो",
        # purchase verbs
        "kharida","kharidi","kharida tha","kharidi thi","bought","purchased",
        "liya tha","liya thi","liye the","liya","li thi","le aaya","le aayi",
        "laya","layi","tha","thi","the",
        "खरीदा","खरीदी","लिया था","लिया थी","लिए थे","लिया","ली थी",
        "ले आया","ले आई","लाया","लायी","लाई","था","थी","थे",
        # temporal
        "aaj","kal","parso","today","yesterday","aaj ka","आज","कल","परसों",
        "pichle hafte","pichhle hafte","last week","पिछले हफ्ते","पिछले सप्ताह",
        "agle hafte","agle mahine","next week","next month",
        "अगले हफ्ते","अगले महीने",
        # expiry
        "expire hoga","kharab hoga","expire ho jayega","kharab ho jayega",
        "mein expire","mein kharab","ko expire","ko kharab",
        "expire","expiry","kharab","एक्सपायर होगा","खराब होगा","एक्सपायर",
        "tak chalega","tak theek rahega","best before","use by",
        # particles
        "ko","se","mein","me","ka","ki","ke","hai","hoga","ho","pe","par",
        "को","से","में","का","की","के","है","होगा","हो","पे","पर",
        ".",",","!","?",
    ]
    for w in strip_words:
        t = re.sub(r'\b' + re.escape(w) + r'\b', " ", t)

    t = " ".join(t.split()).strip()

    # Step 4: CATEGORY_KEYWORDS se exact item keyword dhundo
    for cat, words in CATEGORY_KEYWORDS.items():
        # longest match first
        for kw in sorted(words, key=len, reverse=True):
            if kw in t:
                return kw.title()

    # Step 5: fallback — jo kuch bacha woh check karo
    words_left = t.split()
    if words_left:
        words_left = [w for w in words_left if not w.isdigit() and len(w) > 2]
        if words_left:
            candidate = " ".join(words_left[:2]).title()
            # Validate: sirf valid item return karo
            return candidate if _is_valid_item(candidate) else None

    return None


# ── PRIVATE: keyword fallback parser ─────────────────────────────────────────
def _keyword_parse(text):
    t = text.lower().strip()

    add_words = [
        "add","jodo","jodein","daalo","dalo","naya item",
        "जोड़ो","जोड़ें","डालो","ऐड","एड करो",
        "liya tha","liya thi","liye the","kharida","kharidi",
        "लिया था","लिया थी","लिए थे","खरीदा","खरीदी",
    ]
    expiry_check_words = [
        "expire","expiry","kharab","expir",
        "एक्सपायर","ख़राब","खराब",
    ]
    recipe_words = [
        "recipe","banau","banaye","banayein","cook","kya banu","kya banau",
        "बनाऊं","बनाये","बनाएं","रेसिपी","क्या बनाऊं","क्या बनाये",
    ]

    _null = {"item_name":None,"category":None,"price":None,
             "purchase_date":None,"expiry_date":None}

    has_add = any(w in t for w in add_words)
    has_expiry_kw = any(w in t for w in expiry_check_words)

    # add_item: either explicit add command OR purchase phrase
    if has_add:
        name = _extract_item_name(text)
        category = detect_category(name) or "Food"
        purchase_date = extract_purchase_date(text) or "today"
        expiry_date = extract_expiry_date(text)
        return {"intent":"add_item","item_name":name,"category":category,
                "price":None,"purchase_date":purchase_date,"expiry_date":expiry_date}

    # check_expiry: sirf expire check (no add word)
    if has_expiry_kw and not has_add:
        return {"intent":"check_expiry",**_null}

    if any(w in t for w in recipe_words):
        name = _extract_item_name(text)
        return {"intent":"suggest_recipe","item_name":name,**{k:None for k in _null}}

    return {"intent":"unknown",**_null}


# ── PUBLIC: parse_voice_command ───────────────────────────────────────────────
def parse_voice_command(text):
    """
    Pehle Claude AI se parse karo — clean JSON milta hai.
    Agar API key nahi hai ya error aaya → keyword fallback.
    """
    if ai_client:
        try:
            today_str = date.today().strftime("%Y-%m-%d")
            system_prompt = (
                f"Today is {today_str}. "
                "You parse voice commands for a pantry/shelf tracker app (Predicta Shelf). "
                "User speaks Hindi (Devanagari), English, or Hinglish. "
                "Reply with ONLY a single JSON object — no markdown, no explanation.\n\n"

                "SCHEMA:\n"
                '{"intent":"add_item"|"check_expiry"|"suggest_recipe"|"unknown",'
                '"item_name":string|null,'
                '"category":"Food"|"Groceries"|"Cosmetics"|"Medicine"|"Jewelry"|null,'
                '"price":number|null,'
                '"purchase_date":"YYYY-MM-DD"|null,'
                '"expiry_date":"YYYY-MM-DD"|null}\n\n'

                "ITEM NAME RULE (CRITICAL):\n"
                "Extract ONLY the product noun. 1-2 words maximum.\n"
                "Remove ALL of: dates, numbers, month names, ordinals (1st/2nd/12th), "
                "command words (add/jodo/karo), temporal words (aaj/kal/june/2026), "
                "verb phrases (liya tha/kharida/expire hoga), particles (ko/se/mein/ka).\n"
                "Examples:\n"
                "  'atta 24 june 2026 ko liya tha 6 july ko expire hoga' → item_name='Atta'\n"
                "  'doodh aaj kharida 3 din mein kharab hoga' → item_name='Doodh'\n"
                "  'shampoo add karo 6 mahine mein expire hoga' → item_name='Shampoo'\n"
                "  'milk add karo' → item_name='Milk'\n"
                "  'आटा जोड़ो आज' → item_name='आटा'\n"
                "  'टमाटर लिया था कल' → item_name='टमाटर'\n\n"

                "DATE RULES:\n"
                "Named date format: 'DD MonthName YYYY' (e.g. '24 June 2026', '6 July 2026').\n"
                "If TWO named dates → first=purchase_date, second=expiry_date.\n"
                "If ONE named date + expiry keyword (expire/kharab) → expiry_date only.\n"
                "If ONE named date + purchase keyword (liya/kharida/bought) → purchase_date only.\n"
                "Relative purchase: aaj/today→today, kal/yesterday→today-1, "
                "parso→today-2, X din pehle→today-X, pichle hafte→today-7.\n"
                "Relative expiry: X din mein→today+X, X hafte mein→today+X weeks, "
                "X mahine mein→today+X*30, X saal mein→today+X*365, "
                "agle hafte→today+7, agle mahine→today+30.\n"
                "No date mentioned → null.\n\n"

                "CATEGORY:\n"
                "Food=milk/doodh/paneer/tamatar/anda/bread/kela/seb/chicken/dahi/roti/sabzi\n"
                "Groceries=chawal/atta/tel/chai/biscuit/dal/maggi/ghee/sugar/cheeni\n"
                "Cosmetics=shampoo/soap/lipstick/lotion/perfume/kajal/serum/cream\n"
                "Medicine=tablet/capsule/syrup/dawa/ointment/goli\n"
                "Jewelry=ring/earring/necklace/gold/silver/chain/bangle\n\n"

                f"Today={today_str}. Compute all dates from today."
            )
            resp = ai_client.models.generate_content(
                model=GEMINI_MODEL,
                contents=text,
                config=types.GenerateContentConfig(
                    system_instruction=system_prompt,
                    max_output_tokens=300,
                    response_mime_type="application/json",
                ),
            )
            raw = resp.text.strip()
            raw = raw.replace("```json","").replace("```","").strip()
            result = json.loads(raw)

            # Post-process: AI se aaya item_name bhi clean karo
            if result.get("item_name"):
                result["item_name"] = _clean_ai_name(result["item_name"])
            return result
        except Exception as e:
            print("Voice AI parse failed, keyword fallback:", e)

    return _keyword_parse(text)


def _is_valid_item(name):
    """Check: extracted name actually ek valid pantry item hai?
    CATEGORY_KEYWORDS mein match hona chahiye, warna None return karo."""
    if not name:
        return False
    nl = name.lower().strip()
    if len(nl) <= 2:
        return False
    for words in CATEGORY_KEYWORDS.values():
        for w in words:
            if w in nl or nl in w:
                return True
    return False


def _clean_ai_name(name):
    """AI-returned item name se garbage strip karo, phir validate karo."""
    if not name:
        return name
    name = re.sub(r'\b20\d{2}\b', '', name)
    name = re.sub(_MONTH_ALT, '', name, flags=re.IGNORECASE)
    name = re.sub(r'\b\d+(?:st|nd|rd|th)?\b', '', name)
    fillers = r'\b(ko|se|mein|me|ka|ki|ke|hai|hoga|aaj|kal|the|par|pe|make|jo|bana|bano|karo)\b'
    name = re.sub(fillers, '', name, flags=re.IGNORECASE)
    name = " ".join(name.split()).strip().title()
    cleaned = name or None
    return cleaned if _is_valid_item(cleaned) else None


# ── PUBLIC: generate_recipe_idea ──────────────────────────────────────────────
def generate_recipe_idea(item_name, lang):
    if not ai_client:
        return None
    try:
        prompt = (
            f"Suggest exactly 2 quick Indian home-cook recipes using '{item_name}' as the "
            f"main ingredient. Reply in {'Hindi' if lang == 'hi' else 'English'} in ONE short "
            f"sentence — just the two dish names joined by 'and'/'aur'. Nothing else."
        )
        resp = ai_client.models.generate_content(
            model=GEMINI_MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(max_output_tokens=100),
        )
        return resp.text.strip()
    except Exception as e:
        print("Recipe AI failed:", e)
        return None