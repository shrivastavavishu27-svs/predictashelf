import os
from dotenv import load_dotenv

load_dotenv()

from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session, Response
from datetime import datetime, date, timedelta
from translations import TRANSLATIONS, LANG_NAMES
from functools import wraps
import json, os
import hashlib
import uuid
import base64
from itsdangerous import URLSafeTimedSerializer
import re
import io
from voice_assistant import (
    parse_voice_command,
    generate_recipe_idea,
    extract_purchase_date,
    extract_expiry_date,
    detect_category,
)

app = Flask(__name__)

import json
import os

USERS_FILE = "users.json"
PRODUCTS_FILE = "products.json"

def load_json(file):
    if not os.path.exists(file):
        with open(file, "w") as f:
            json.dump([], f)

    with open(file, "r") as f:
        return json.load(f)

def save_json(file, data):
    with open(file, "w") as f:
        json.dump(data, f, indent=4)

app.secret_key = os.getenv("secret_key", "shelfwise2025")

# Password reset token serializer
password_serializer = URLSafeTimedSerializer(app.secret_key)

# ── SHELF LIFE (days) ──────────────────────────────────────────────────────
SHELF_LIFE = {
    "milk":3,"doodh":3,"dudh":3,"cream":5,"butter":30,"cheese":14,
    "paneer":4,"yogurt":7,"dahi":5,"curd":5,"bread":6,"pav":4,"roti":2,
    "egg":21,"anda":21,"inda":21,"chicken":2,"mutton":2,
    "tomato":5,"tamatar":5,"onion":30,"pyaz":30,"dungri":30,
    "potato":14,"aloo":14,"batata":14,"carrot":10,"gajar":10,
    "spinach":4,"palak":4,"cabbage":7,"capsicum":7,"broccoli":5,
    "apple":14,"seb":14,"banana":5,"kela":5,"kandu":5,
    "mango":5,"aam":5,"keri":5,"orange":10,"grapes":7,"papaya":5,
    "juice":3,"rice":365,"chawal":365,"flour":180,"atta":180,
    "maida":180,"oil":365,"tel":365,"ghee":180,"sugar":730,
    "cheeni":730,"dal":180,"noodles":180,"maggi":180,"pasta":365,
    "biscuit":90,"chocolate":180,"chips":60,"sauce":30,"ketchup":30,
    "pickle":180,"achar":180,"jam":90,"honey":730,"shehad":730,
    "namkeen":60,"chhola masala":270,"chhole masala":270,"pav bhaji masala":270,
    "moisturizer":365,"lotion":365,"sunscreen":180,"face wash":365,
    "toner":365,"serum":365,"scrub":180,"lipstick":365,"lip gloss":180,
    "foundation":180,"concealer":365,"mascara":90,"kajal":180,
    "eyeliner":180,"eyeshadow":730,"shampoo":365,"conditioner":365,
    "hair oil":365,"body wash":365,"soap":365,"deodorant":365,
    "perfume":730,"nail polish":365,"tablet":365,"capsule":365,
    "syrup":180,"ointment":365,"tea":730,"coffee":365,"oats":365,
    "default_Food":7,"default_Cosmetics":365,
    "default_Medicine":365,"default_Groceries":90,"default_Jewelry":730,
}

RECIPES = {
    "milk": [
        {"name_en":"Kheer","name_hi":"खीर","time":"30 min","emoji":"🍚","ingredients":"Milk, Rice, Sugar, Cardamom","tip_en":"Use full-fat milk for creamier texture.","tip_hi":"मलाईदार खीर के लिए फुल-फैट दूध इस्तेमाल करें।"},
        {"name_en":"Homemade Paneer","name_hi":"घर का पनीर","time":"20 min","emoji":"🧀","ingredients":"Milk, Lemon juice","tip_en":"Boil milk, add lemon, strain through muslin.","tip_hi":"दूध उबालें, नींबू डालें, मलमल से छानें।"},
        {"name_en":"Chai","name_hi":"चाय","time":"5 min","emoji":"☕","ingredients":"Milk, Tea leaves, Sugar, Ginger","tip_en":"Add cardamom for masala chai flavor.","tip_hi":"मसाला चाय के लिए इलायची डालें।"},
        {"name_en":"White Sauce Pasta","name_hi":"व्हाइट सॉस पास्ता","time":"25 min","emoji":"🍝","ingredients":"Milk, Butter, Flour, Pasta, Cheese","tip_en":"Stir continuously to avoid lumps.","tip_hi":"गांठ से बचने के लिए लगातार हिलाते रहें।"},
    ],
    "bread": [
        {"name_en":"French Toast","name_hi":"फ्रेंच टोस्ट","time":"10 min","emoji":"🍞","ingredients":"Bread, Egg, Milk, Sugar, Cinnamon","tip_en":"Soak bread 30 seconds each side.","tip_hi":"ब्रेड को दोनों तरफ 30 सेकंड भिगोएं।"},
        {"name_en":"Bread Upma","name_hi":"ब्रेड उपमा","time":"15 min","emoji":"🫓","ingredients":"Bread, Onion, Tomato, Mustard, Curry leaves","tip_en":"Toast bread cubes separately first.","tip_hi":"ब्रेड क्यूब्स पहले अलग से टोस्ट करें।"},
        {"name_en":"Bread Pakora","name_hi":"ब्रेड पकोड़ा","time":"20 min","emoji":"🟡","ingredients":"Bread, Besan, Potato, Spices, Oil","tip_en":"Add ajwain to batter for digestion.","tip_hi":"पाचन के लिए बेसन में अजवाइन डालें।"},
    ],
    "egg": [
        {"name_en":"Masala Omelette","name_hi":"मसाला ऑमलेट","time":"8 min","emoji":"🍳","ingredients":"Eggs, Onion, Tomato, Green chilli, Coriander","tip_en":"Add a splash of water for fluffier omelette.","tip_hi":"फुलाने के लिए थोड़ा पानी मिलाएं।"},
        {"name_en":"Egg Bhurji","name_hi":"अंडा भुर्जी","time":"12 min","emoji":"🥘","ingredients":"Eggs, Onion, Tomato, Spices, Butter","tip_en":"Cook on low heat, stir constantly.","tip_hi":"धीमी आंच पर पकाएं, लगातार हिलाते रहें।"},
    ],
    "banana": [
        {"name_en":"Banana Smoothie","name_hi":"केला स्मूदी","time":"5 min","emoji":"🥤","ingredients":"Banana, Milk, Honey, Ice","tip_en":"Freeze overripe bananas for creamier result.","tip_hi":"ज्यादा पके केले फ्रीज करें — क्रीमी होगी।"},
        {"name_en":"Banana Pancake","name_hi":"केला पैनकेक","time":"15 min","emoji":"🥞","ingredients":"Banana, Egg, Oats","tip_en":"Just 3 ingredients — naturally sweet!","tip_hi":"सिर्फ 3 सामग्री — प्राकृतिक रूप से मीठा!"},
    ],
    "tomato": [
        {"name_en":"Tomato Soup","name_hi":"टमाटर सूप","time":"20 min","emoji":"🍅","ingredients":"Tomatoes, Onion, Garlic, Cream, Basil","tip_en":"Roast tomatoes first for deeper flavor.","tip_hi":"गहरे स्वाद के लिए टमाटर पहले भूनें।"},
        {"name_en":"Tomato Chutney","name_hi":"टमाटर चटनी","time":"15 min","emoji":"🫙","ingredients":"Tomatoes, Garlic, Red chilli, Oil, Mustard","tip_en":"Add tamarind for extra tanginess.","tip_hi":"खट्टापन बढ़ाने के लिए इमली डालें।"},
    ],
    "yogurt": [
        {"name_en":"Raita","name_hi":"रायता","time":"5 min","emoji":"🥗","ingredients":"Yogurt, Cucumber, Cumin, Salt, Coriander","tip_en":"Squeeze out cucumber water before mixing.","tip_hi":"मिलाने से पहले खीरे का पानी निचोड़ें।"},
        {"name_en":"Lassi","name_hi":"लस्सी","time":"5 min","emoji":"🥛","ingredients":"Yogurt, Sugar/Salt, Cardamom, Ice","tip_en":"Sweet: add rose water. Salty: add cumin.","tip_hi":"मीठी: गुलाब जल। नमकीन: जीरा डालें।"},
    ],
    "dahi": [
        {"name_en":"Raita","name_hi":"रायता","time":"5 min","emoji":"🥗","ingredients":"Dahi, Cucumber, Cumin, Salt, Coriander","tip_en":"Squeeze out cucumber water before mixing.","tip_hi":"मिलाने से पहले खीरे का पानी निचोड़ें।"},
        {"name_en":"Lassi","name_hi":"लस्सी","time":"5 min","emoji":"🥛","ingredients":"Dahi, Sugar/Salt, Cardamom, Ice","tip_en":"Sweet: add rose water. Salty: add cumin.","tip_hi":"मीठी: गुलाब जल। नमकीन: जीरा डालें।"},
    ],
}

TOXIC_INFO = {
    "en": {
        "Food":     [{"name":"MSG (E621)","risk":"high"},{"name":"Sodium Benzoate","risk":"moderate"},
                     {"name":"Artificial Colors","risk":"high"},{"name":"Trans Fat","risk":"high"},{"name":"HFCS","risk":"high"}],
        "Cosmetics":[{"name":"Parabens","risk":"high"},{"name":"SLS/SLES","risk":"moderate"},
                     {"name":"Formaldehyde","risk":"critical"},{"name":"Phthalates","risk":"high"},{"name":"Mercury","risk":"critical"}],
        "Groceries":[{"name":"BHA/BHT","risk":"moderate"},{"name":"Sodium Nitrate","risk":"high"}],
        "Medicine": [{"name":"Expired Compounds","risk":"critical"}],
    },
    "hi": {
        "Food":     [{"name":"MSG (E621) — स्वाद बढ़ाने वाला रसायन","risk":"high"},{"name":"सोडियम बेंजोएट — परिरक्षक","risk":"moderate"},
                     {"name":"कृत्रिम रंग — आर्टिफिशियल कलर","risk":"high"},{"name":"ट्रांस फैट — हानिकारक वसा","risk":"high"},{"name":"HFCS — उच्च फ्रुक्टोज़ शर्करा","risk":"high"}],
        "Cosmetics":[{"name":"पैराबेन्स — केमिकल प्रिजर्वेटिव","risk":"high"},{"name":"SLS/SLES — झाग वाला रसायन","risk":"moderate"},
                     {"name":"फॉर्मेल्डिहाइड — जहरीला रसायन","risk":"critical"},{"name":"थैलेट्स — हार्मोन हानिकारक","risk":"high"},{"name":"पारा (Mercury)","risk":"critical"}],
        "Groceries":[{"name":"BHA/BHT — एंटीऑक्सीडेंट केमिकल","risk":"moderate"},{"name":"सोडियम नाइट्रेट — मांस परिरक्षक","risk":"high"}],
        "Medicine": [{"name":"एक्सपायर्ड यौगिक — उपयोग न करें","risk":"critical"}],
    },
}

# ── HELPER FUNCTIONS ────────────────────────────────────────────────────────

def fix_day_plural(text, n):
    """English 'day(s)' placeholder ko n ke hisaab se 'day' ya 'days' bana do
    (n==1/-1 -> 'day', warna 'days'). Hindi strings mein 'day(s)' nahi hota,
    so unpe yeh no-op rahega."""
    return text.replace("day(s)", "day" if abs(n) == 1 else "days")

def get_status(expiry_str):
    """Returns (status, days, label_text) with proper {n} replacement"""
    try:
        exp = datetime.strptime(expiry_str, "%Y-%m-%d").date()
        today = date.today()
        diff = (exp - today).days
        lang = get_lang()
        T = TRANSLATIONS.get(lang, TRANSLATIONS["en"])

        if diff < 0:
            n = abs(diff)
            label = T.get("status_expired", "💀 Expired")
            return "expired", n, label
        elif diff == 0:
            label = T.get("status_today", "🚨 Today!")
            return "today", 0, label
        elif diff <= 2:
            label = T.get("status_critical", "⚡ Only {n} day(s)!").replace("{n}", str(diff))
            label = fix_day_plural(label, diff)
            return "critical", diff, label
        elif diff <= 7:
            label = T.get("status_warning", "⚠️ {n} days remaining").replace("{n}", str(diff))
            return "warning", diff, label
        else:
            label = T.get("status_good", "✅ {n} days fresh").replace("{n}", str(diff))
            return "good", diff, label
    except:
        return "unknown", 0, ""

def get_recipes_for(name):
    nl = name.lower()
    for k, v in RECIPES.items():
        if k in nl:
            return v
    return []

def get_notifications(products):
    notifs = []
    today = date.today()
    lang = get_lang()
    T = TRANSLATIONS.get(lang, TRANSLATIONS["en"])

    for p in products:
        try:
            exp = datetime.strptime(p["expiry"], "%Y-%m-%d").date()
            diff = (exp - today).days
            item_name = translate_item_name(p["name"])
            recipes = get_recipes_for(p["name"])
            rname = recipes[0].get(f"name_{lang}", recipes[0]["name_en"]) if recipes else ""
            rtxt = f" {T.get('try_making', '')} {rname}!" if rname else ""
            expiry_formatted = exp.strftime("%d %b %Y")

            if diff < 0:
                days_ago = abs(diff)
                if lang == 'hi':
                    title = f"{item_name} — {days_ago} दिन पहले एक्सपायर हो गया"
                    msg = f"{expiry_formatted} को एक्सपायर हो गया। {T['notif_expired_msg']}"
                else:
                    title = f"{item_name} — {fix_day_plural(f'Expired {days_ago} day(s) ago', days_ago)}"
                    msg = f"Expired on {expiry_formatted}. {T['notif_expired_msg']}"
                notifs.append({"type":"expired","icon":"💀","title":title,"msg":msg,"product":p})

            elif diff == 0:
                if lang == 'hi':
                    title = f"{item_name} — आज एक्सपायर हो रहा है!"
                    msg = f"आज एक्सपायर हो रहा है! {T['notif_today_msg']}{rtxt}"
                else:
                    title = f"{item_name} — Expires TODAY!"
                    msg = f"Expiring today! {T['notif_today_msg']}{rtxt}"
                notifs.append({"type":"critical","icon":"🚨","title":title,"msg":msg,"product":p})

            elif diff == 1:
                if lang == 'hi':
                    title = f"{item_name} — कल एक्सपायर होगा"
                    msg = f"{expiry_formatted} को एक्सपायर होगा। {T['notif_tomorrow_msg']}{rtxt}"
                else:
                    title = f"{item_name} — Expires TOMORROW"
                    msg = f"Expires on {expiry_formatted}. {T['notif_tomorrow_msg']}{rtxt}"
                notifs.append({"type":"warning","icon":"⚠️","title":title,"msg":msg,"product":p})

            elif diff <= 3:
                if lang == 'hi':
                    title = f"{item_name} — {diff} दिन में एक्सपायर होगा"
                    msg = f"{expiry_formatted} को एक्सपायर होगा। {T['notif_soon_msg']}{rtxt}"
                else:
                    title = f"{item_name} — Expires in {diff} days"
                    msg = f"Expires on {expiry_formatted}. {T['notif_soon_msg']}{rtxt}"
                notifs.append({"type":"soon","icon":"🕐","title":title,"msg":msg,"product":p})

            elif diff <= 7:
                if lang == 'hi':
                    title = f"{item_name} — {diff} दिन में एक्सपायर होगा"
                    msg = f"{expiry_formatted} को एक्सपायर होगा। जल्दी उपयोग करने की योजना बनाएं।"
                else:
                    title = f"{item_name} — Expires in {diff} days"
                    msg = f"Expires on {expiry_formatted}. Plan to use it soon."
                notifs.append({"type":"upcoming","icon":"📅","title":title,"msg":msg,"product":p})

        except:
            pass
    return notifs

def get_lang():
    return session.get("lang", "en")

def t(key):
    lang = get_lang()
    return TRANSLATIONS.get(lang, TRANSLATIONS["en"]).get(key, TRANSLATIONS["en"].get(key, key))

def translate_item_name(name):
    """Translate item name based on current language"""
    lang = get_lang()
    if lang == "en":
        return name
    name_lower = name.lower()
    # Exact match
    item_key = f"item_{name_lower}"
    if item_key in TRANSLATIONS.get(lang, {}):
        return TRANSLATIONS[lang][item_key]
    # Partial match
    for key, translation in TRANSLATIONS.get(lang, {}).items():
        if key.startswith("item_") and key[5:] in name_lower:
            return translation
    return name

# ── DATABASE HELPERS (JSON file storage) ─────────────────────────────────────
# MySQL hata diya gaya hai. Ab sab kuch teen JSON files mein store hota hai:
# users.json (dict keyed by username), products.json (list), removed_items.json (list).

REMOVED_ITEMS_FILE = "removed_items.json"

def _load_users_dict():
    if not os.path.exists(USERS_FILE):
        with open(USERS_FILE, "w") as f:
            json.dump({}, f)
    with open(USERS_FILE, "r") as f:
        return json.load(f)

def _save_users_dict(data):
    with open(USERS_FILE, "w") as f:
        json.dump(data, f, indent=4)

def db_get_user(username):
    users = _load_users_dict()
    return users.get(username)

def db_get_user_by_email(email):
    users = _load_users_dict()
    for user in users.values():
        if user.get("email") == email:
            return user
    return None

def db_create_user(user):
    users = _load_users_dict()
    users[user['username']] = {
        "id": user['id'],
        "username": user['username'],
        "email": user['email'],
        "password": user['password'],
        "full_name": user.get('full_name', ''),
        "created_at": user.get('created_at'),
        "updated_at": user.get('updated_at'),
        "is_active": user.get('is_active', True),
        "theme": user.get('theme', 'dark'),
    }
    _save_users_dict(users)

def db_update_user(username, fields):
    if not fields:
        return
    users = _load_users_dict()
    if username in users:
        users[username].update(fields)
        _save_users_dict(users)

def db_delete_user(username):
    users = _load_users_dict()
    if username in users:
        del users[username]
        _save_users_dict(users)

def db_get_products(user_id=None):
    products = load_json(PRODUCTS_FILE)
    if user_id is not None:
        return [p for p in products if p.get('user_id') == user_id]
    return products

def db_add_product(p):
    products = load_json(PRODUCTS_FILE)
    products.append(p)
    save_json(PRODUCTS_FILE, products)

def db_delete_product(pid, user_id):
    """Item delete karke return karta hai (None agar mila nahi)."""
    products = load_json(PRODUCTS_FILE)
    found = None
    remaining = []
    for p in products:
        if str(p.get('id')) == str(pid) and p.get('user_id') == user_id:
            found = p
        else:
            remaining.append(p)
    if found is not None:
        save_json(PRODUCTS_FILE, remaining)
    return found

def db_clear_user_products(user_id):
    products = load_json(PRODUCTS_FILE)
    remaining = [p for p in products if p.get('user_id') != user_id]
    save_json(PRODUCTS_FILE, remaining)

def db_get_removed_items(user_id=None):
    items = load_json(REMOVED_ITEMS_FILE)
    if user_id is not None:
        return [p for p in items if p.get('user_id') == user_id]
    return items

def db_add_removed_item(p):
    items = load_json(REMOVED_ITEMS_FILE)
    items.append(p)
    save_json(REMOVED_ITEMS_FILE, items)

def db_delete_removed_item(pid, user_id):
    """Item delete karke return karta hai (None agar mila nahi)."""
    items = load_json(REMOVED_ITEMS_FILE)
    found = None
    remaining = []
    for p in items:
        if str(p.get('id')) == str(pid) and p.get('user_id') == user_id:
            found = p
        else:
            remaining.append(p)
    if found is not None:
        save_json(REMOVED_ITEMS_FILE, remaining)
    return found

def hash_password(password):
    salt = "shelfwise_salt_2025"
    return hashlib.sha256((password + salt).encode()).hexdigest()

def validate_password(password):
    if len(password) < 8:
        return False, "Password must be at least 8 characters long"
    if not re.search(r"[A-Z]", password):
        return False, "Password must contain at least one uppercase letter"
    if not re.search(r"[a-z]", password):
        return False, "Password must contain at least one lowercase letter"
    if not re.search(r"\d", password):
        return False, "Password must contain at least one digit"
    return True, "Password is valid"

def validate_email(email):
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def generate_reset_token(email):
    return password_serializer.dumps(email, salt='password-reset-salt')

def verify_reset_token(token, max_age=3600):
    try:
        email = password_serializer.loads(token, salt='password-reset-salt', max_age=max_age)
        return email
    except:
        return None

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'logged_in' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def auto_shelf_days(name, category):
    nl = name.lower()
    # Longest keyword first, so a specific multi-word match (e.g. "pav bhaji
    # masala") wins over a shorter generic substring (e.g. "pav") that
    # happens to also appear inside it.
    for k in sorted(SHELF_LIFE.keys(), key=len, reverse=True):
        if not k.startswith("default_") and k in nl:
            return SHELF_LIFE[k]
    return SHELF_LIFE.get(f"default_{category}", 7)

def detect_metal(name):
    nl = name.lower()
    for m in ["silver", "gold", "platinum", "copper", "brass"]:
        if m in nl:
            return m
    return None

# ── AUTH ROUTES ─────────────────────────────────────────────────────────────

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()
        user = db_get_user(username)
        if user and user["password"] == hash_password(password):
            session['logged_in'] = True
            session['username'] = username
            session['user_id'] = user["id"]
            session['theme'] = user.get('theme', 'dark')
            flash("success|Login successful! Welcome back.")
            return redirect(url_for("index"))
        else:
            flash("error|Invalid username or password. Please try again.")
            return redirect(url_for("login"))
    if 'theme' not in session:
        session['theme'] = 'dark'
    lang = session.get('lang', 'en')
    T = TRANSLATIONS.get(lang, TRANSLATIONS["en"])
    return render_template("login.html", lang=lang, T=T)

@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "").strip()
        confirm_password = request.form.get("confirm_password", "").strip()
        full_name = request.form.get("full_name", "").strip()
        if not username or not email or not password or not confirm_password:
            flash("error|All fields are required!")
            return redirect(url_for("signup"))
        if password != confirm_password:
            flash("error|Passwords do not match!")
            return redirect(url_for("signup"))
        is_valid, password_msg = validate_password(password)
        if not is_valid:
            flash(f"error|{password_msg}")
            return redirect(url_for("signup"))
        if not validate_email(email):
            flash("error|Please enter a valid email address!")
            return redirect(url_for("signup"))
        if db_get_user(username):
            flash("error|Username already exists!")
            return redirect(url_for("signup"))
        if db_get_user_by_email(email):
            flash("error|Email already registered!")
            return redirect(url_for("signup"))
        user_id = str(uuid.uuid4())
        db_create_user({
            "id": user_id,
            "username": username,
            "email": email,
            "password": hash_password(password),
            "full_name": full_name,
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "updated_at": None,
            "is_active": True,
            "theme": "dark"
        })
        flash("success|Registration successful! Please login.")
        return redirect(url_for("login"))
    if 'theme' not in session:
        session['theme'] = 'dark'
    lang = session.get('lang', 'en')
    T = TRANSLATIONS.get(lang, TRANSLATIONS["en"])
    return render_template("signup.html", lang=lang, T=T)

@app.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():
    lang = session.get('lang', 'en')
    T = TRANSLATIONS.get(lang, TRANSLATIONS["en"])
    if request.method == "POST":
        email = request.form.get("email", "").strip()
        if not validate_email(email):
            flash("error|Please enter a valid email address!")
            return redirect(url_for("forgot_password"))
        user = db_get_user_by_email(email)
        if user:
            token = generate_reset_token(email)
            reset_link = url_for('reset_password', token=token, _external=True)
            return render_template("forgot_password.html", lang=lang, T=T, reset_link=reset_link)
        else:
            flash("error|No account found with that email address!")
            return redirect(url_for("forgot_password"))
    return render_template("forgot_password.html", lang=lang, T=T)

@app.route("/reset-password/<token>", methods=["GET", "POST"])
def reset_password(token):
    email = verify_reset_token(token)
    if not email:
        flash("error|Invalid or expired reset link!")
        return redirect(url_for("login"))
    if request.method == "POST":
        password = request.form.get("password", "").strip()
        confirm_password = request.form.get("confirm_password", "").strip()
        if password != confirm_password:
            flash("error|Passwords do not match!")
            return redirect(url_for('reset_password', token=token))
        is_valid, password_msg = validate_password(password)
        if not is_valid:
            flash(f"error|{password_msg}")
            return redirect(url_for('reset_password', token=token))
        user = db_get_user_by_email(email)
        if user:
            db_update_user(user["username"], {
                "password": hash_password(password),
                "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            })
        flash("success|Password reset successful! Please login.")
        return redirect(url_for("login"))
    lang = session.get('lang', 'en')
    T = TRANSLATIONS.get(lang, TRANSLATIONS["en"])
    return render_template("reset_password.html", token=token, lang=lang, T=T)

@app.route("/logout")
def logout():
    session.clear()
    flash("success|You have been logged out successfully.")
    return redirect(url_for("login"))

# ── PROFILE ─────────────────────────────────────────────────────────────────

@app.route("/profile")
@login_required
def profile():
    username = session.get('username', 'admin')
    user_data = db_get_user(username) or {
        'username': username,
        'full_name': username.capitalize(),
        'email': '',
        'created_at': 'Unknown',
        'updated_at': 'Never'
    }
    session['full_name'] = user_data.get('full_name', username.capitalize())
    session['email'] = user_data.get('email', '')
    session['created_at'] = user_data.get('created_at', 'Unknown')
    session['updated_at'] = user_data.get('updated_at', 'Never')

    user_products = db_get_products(session.get('user_id'))
    lang = get_lang()
    T = TRANSLATIONS.get(lang, TRANSLATIONS["en"])

    # Compute per-user stats
    for p in user_products:
        status, days, msg = get_status(p["expiry"])
        p["status"] = status

    count_expired  = sum(1 for p in user_products if p["status"] == "expired")
    count_today    = sum(1 for p in user_products if p["status"] == "today")
    count_soon     = sum(1 for p in user_products if p["status"] in ["critical", "warning"])
    count_fresh    = sum(1 for p in user_products if p["status"] == "good")

    # Account activity summary
    member_days = 0
    try:
        created = datetime.strptime(user_data.get("created_at", "").split(".")[0], "%Y-%m-%d %H:%M:%S")
        member_days = max((datetime.now() - created).days, 0)
    except Exception:
        member_days = 0

    removed_items = db_get_removed_items(session.get('user_id'))
    total_items_added = len(user_products) + len(removed_items)

    return render_template("profile.html",
                           user=user_data,
                           products=user_products,
                           products_count=len(user_products),
                           count_expired=count_expired,
                           count_today=count_today,
                           count_soon=count_soon,
                           count_fresh=count_fresh,
                           member_days=member_days,
                           total_items_added=total_items_added,
                           lang=lang, T=T)

@app.route("/update-profile", methods=["POST"])
@login_required
def update_profile():
    username = session.get('username')
    full_name = request.form.get("full_name", "").strip()
    email = request.form.get("email", "").strip()
    if email and not validate_email(email):
        flash("error|Please enter a valid email address!")
        return redirect(url_for("profile", tab=request.form.get("tab", "overview")))
    db_update_user(username, {
        "full_name": full_name,
        "email": email,
        "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    })
    session['full_name'] = full_name
    session['email'] = email
    session['updated_at'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    lang = get_lang()
    T = TRANSLATIONS[lang]
    flash(f"success|{T.get('update_profile', 'Profile updated successfully!')}")
    return redirect(url_for("profile", tab=request.form.get("tab", "overview")))

# ── LANGUAGE ─────────────────────────────────────────────────────────────────

@app.route("/set-lang/<lang>")
@login_required
def set_lang(lang):
    if lang in ["en", "hi"]:   # Only en and hi — Gujarati removed
        session["lang"] = lang
    return redirect(request.referrer or url_for("index"))

# ── MAIN PAGES ───────────────────────────────────────────────────────────────

@app.route("/")
def opening():
    if 'theme' not in session:
        session['theme'] = 'dark'
    return render_template("opening.html")

@app.route("/index")
@login_required
def index():
    user_products = db_get_products(session.get('user_id'))
    lang = get_lang()
    T = TRANSLATIONS.get(lang, TRANSLATIONS["en"])

    for p in user_products:
        status, days, msg = get_status(p["expiry"])
        p["status"] = status
        p["days_left"] = days
        p["status_msg"] = msg
        p["recipes"] = get_recipes_for(p["name"]) if p.get("category") in ["Food", "Groceries"] else []
        lang_key = get_lang()
        toxic_lang = TOXIC_INFO.get(lang_key, TOXIC_INFO["en"])
        p["toxic"] = toxic_lang.get(p.get("category", "Food"), [])

    # Sort: expired first, then today, critical, warning, good
    sort_order = {"expired": 0, "today": 1, "critical": 2, "warning": 3, "good": 4, "unknown": 5}
    user_products.sort(key=lambda x: sort_order.get(x["status"], 5))

    notifications = get_notifications(user_products)

    return render_template("index.html",
        products=user_products,
        notifications=notifications,
        total=len(user_products),
        expired=sum(1 for p in user_products if p["status"] == "expired"),
        today_alert=sum(1 for p in user_products if p["status"] == "today"),
        expiring_today=sum(1 for p in user_products if p["status"] == "today"),   # for template stat card
        critical=sum(1 for p in user_products if p["status"] == "critical"),
        expiring_soon=sum(1 for p in user_products if p["status"] in ["critical", "warning"]),
        good=sum(1 for p in user_products if p["status"] == "good"),
        lang=lang, T=T, TRANSLATIONS=TRANSLATIONS,
        translate_item_name=translate_item_name)

@app.route("/form")
@login_required
def form():
    lang = get_lang()
    return render_template("form.html", lang=lang, T=TRANSLATIONS[lang], TRANSLATIONS=TRANSLATIONS)

@app.route("/add", methods=["POST"])
@login_required
def add_product():
    lang = get_lang()
    T = TRANSLATIONS[lang]
    name = request.form.get("name", "").strip()
    category = request.form.get("category", "Food")
    purchase = request.form.get("purchase_date", "") or date.today().strftime("%Y-%m-%d")
    expiry_override = request.form.get("expiry_override", "")
    note = request.form.get("note", "").strip()
    price = request.form.get("price", "0") or "0"

    if not name:
        flash(f"error|{T['flash_error_name']}")
        return redirect(url_for("form"))

    if expiry_override:
        expiry = expiry_override
    else:
        try:
            pd = datetime.strptime(purchase, "%Y-%m-%d").date()
        except:
            pd = date.today()
        expiry = (pd + timedelta(days=auto_shelf_days(name, category))).strftime("%Y-%m-%d")

    db_add_product({
        "id": int(datetime.now().timestamp() * 1000),
        "name": name,
        "category": category,
        "expiry": expiry,
        "purchase_date": purchase,
        "note": note,
        "price": price,
        "user_id": session.get('user_id'),
        "added": date.today().strftime("%Y-%m-%d")
    })
    flash(f"success|{name} {T['flash_success']} {expiry}")
    return redirect(url_for("index"))

@app.route("/delete/<int:pid>")
@login_required
def delete_product(pid):
    user_id = session.get('user_id')
    removed = db_delete_product(pid, user_id)

    if removed:
        removed["removed_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        removed["status"] = "removed"
        db_add_removed_item(removed)
        lang = get_lang()
        T = TRANSLATIONS[lang]
        flash(f"success|{removed['name']} {T.get('flash_removed', 'removed successfully!')}")

    return redirect(url_for("index"))

# ── REMOVED ITEMS ────────────────────────────────────────────────────────────

@app.route("/removed-items")
@login_required
def removed_items():
    lang = get_lang()
    T = TRANSLATIONS[lang]
    user_id = session.get('user_id')
    user_removed = db_get_removed_items(user_id)
    # Auto-delete items older than 30 days (from the displayed list)
    cutoff = datetime.now() - timedelta(days=30)
    user_removed = [
        p for p in user_removed
        if datetime.strptime(p.get("removed_at", "2000-01-01 00:00:00"), "%Y-%m-%d %H:%M:%S") > cutoff
    ]
    return render_template("removed_items.html",
                           removed_items=user_removed,
                           lang=lang, T=T)

@app.route("/restore/<int:pid>")
@login_required
def restore_item(pid):
    user_id = session.get('user_id')
    item = db_delete_removed_item(pid, user_id)

    if item:
        item.pop("removed_at", None)
        item.pop("status", None)
        db_add_product(item)
        lang = get_lang()
        T = TRANSLATIONS[lang]
        flash(f"success|{item['name']} {T.get('flash_restored', 'restored successfully!')}")

    return redirect(url_for("removed_items"))

@app.route("/permanent-delete/<int:pid>")
@login_required
def permanent_delete(pid):
    user_id = session.get('user_id')
    item = db_delete_removed_item(pid, user_id)

    if item:
        lang = get_lang()
        T = TRANSLATIONS[lang]
        flash(f"success|{item.get('name', '')} {T.get('flash_permanently_deleted', 'permanently deleted!')}")

    return redirect(url_for("removed_items"))

# ── API ──────────────────────────────────────────────────────────────────────

@app.route("/api/shelf-info")
def shelf_info():
    name = request.args.get("name", "")
    category = request.args.get("category", "Food")
    purchase = request.args.get("purchase", date.today().strftime("%Y-%m-%d"))
    days = auto_shelf_days(name, category)
    try:
        pd = datetime.strptime(purchase, "%Y-%m-%d").date()
        expiry = (pd + timedelta(days=days)).strftime("%Y-%m-%d")
        diff = (pd + timedelta(days=days) - date.today()).days
    except:
        expiry = ""
        diff = days
    metal = detect_metal(name)
    return jsonify({
        "shelf_days": days,
        "expiry": expiry,
        "days_left": diff,
        "metal": metal,
    })

@app.route("/api/voice", methods=["POST"])
@login_required
def voice_assistant():
    data = request.get_json(silent=True) or {}
    text = (data.get("text") or "").strip()
    lang = get_lang()

    if not text:
        reply = "Kuch sunayi nahi diya, dobara boliye." if lang == "hi" else "I didn't catch that, please try again."
        return jsonify({"reply": reply, "intent": "unknown", "success": False})

    parsed = parse_voice_command(text)
    intent = parsed.get("intent", "unknown")

    # ── ADD ITEM ──────────────────────────────────────────────────────────
    if intent == "add_item":
        name = (parsed.get("item_name") or "").strip()
        if not name:
            reply = "Item ka naam nahi pehchana — sirf item ka naam boliye, jaise 'doodh', 'atta', 'shampoo'." if lang == "hi" else "Could not recognise the item name — please say just the item, like 'milk', 'atta', or 'shampoo'."
            return jsonify({"reply": reply, "intent": intent, "success": False})

        category = detect_category(name) or parsed.get("category") or "Food"

        local_date = extract_purchase_date(text)
        purchase_raw = local_date or parsed.get("purchase_date") or "today"
        purchase = date.today().strftime("%Y-%m-%d") if purchase_raw == "today" else purchase_raw
        try:
            pd_date = datetime.strptime(purchase, "%Y-%m-%d").date()
        except Exception:
            pd_date = date.today()
            purchase = pd_date.strftime("%Y-%m-%d")

        # User-specified expiry takes priority over auto-calculated shelf life
        manual_expiry = extract_expiry_date(text) or parsed.get("expiry_date")
        if manual_expiry:
            expiry = manual_expiry
            expiry_source = "manual"
        else:
            expiry = (pd_date + timedelta(days=auto_shelf_days(name, category))).strftime("%Y-%m-%d")
            expiry_source = "auto"

        price = parsed.get("price") or "0"

        db_add_product({
            "id": int(datetime.now().timestamp() * 1000),
            "name": name,
            "category": category,
            "expiry": expiry,
            "purchase_date": purchase,
            "note": "",
            "price": str(price),
            "user_id": session.get('user_id'),
            "added": date.today().strftime("%Y-%m-%d")
        })

        purchase_label = "aaj" if purchase == date.today().strftime("%Y-%m-%d") else purchase
        if lang == "hi":
            if expiry_source == "manual":
                reply = f"{name} ({category}) add ho gaya. Aapne bataya ki yeh {expiry} ko expire hoga."
            else:
                reply = (f"{name} ({category}) add ho gaya, {purchase_label} kharida hua maan ke. "
                         f"Ye {expiry} tak theek rahega.")
        else:
            if expiry_source == "manual":
                reply = f"{name} added under {category}. You said it expires on {expiry}."
            else:
                reply = (f"{name} added under {category}, purchased on {purchase}. "
                         f"It should stay good until {expiry}.")
        return jsonify({"reply": reply, "intent": intent, "success": True, "reload": True})

    # ── CHECK EXPIRY ──────────────────────────────────────────────────────
    elif intent == "check_expiry":
        user_products = db_get_products(session.get('user_id'))
        urgent = []
        for p in user_products:
            status, days, _ = get_status(p["expiry"])
            if status in ("expired", "today", "critical"):
                urgent.append((p["name"], status, days))

        if not urgent:
            reply = "Abhi koi item expire nahi ho raha, sab theek hai!" if lang == "hi" \
                else "Nothing is expiring soon, you're all good!"
        else:
            parts = []
            for name, status, days in urgent[:5]:
                if status == "expired":
                    parts.append(f"{name} ({days} din pehle expire ho gaya)" if lang == "hi"
                                  else fix_day_plural(f"{name} (expired {days} day(s) ago)", days))
                elif status == "today":
                    parts.append(f"{name} (aaj expire ho raha hai)" if lang == "hi"
                                  else f"{name} (expiring today)")
                else:
                    parts.append(f"{name} ({days} din baaki)" if lang == "hi"
                                  else fix_day_plural(f"{name} ({days} day(s) left)", days))
            joined = ", ".join(parts)
            reply = f"Dhyan dein: {joined}." if lang == "hi" else f"Heads up: {joined}."

        return jsonify({"reply": reply, "intent": intent, "success": True})

    # ── SUGGEST RECIPE ────────────────────────────────────────────────────
    elif intent == "suggest_recipe":
        item_name = (parsed.get("item_name") or "").strip()
        recipes = get_recipes_for(item_name) if item_name else []

        if recipes:
            top = recipes[:2]
            names = [r.get(f"name_{lang}", r["name_en"]) for r in top]
            reply = f"{item_name} se aap ye bana sakte hain: {', '.join(names)}." if lang == "hi" \
                else f"With {item_name}, you can make: {', '.join(names)}."
            return jsonify({"reply": reply, "intent": intent, "success": True, "recipes": top})

        idea = generate_recipe_idea(item_name, lang) if item_name else None
        if idea:
            reply = f"{item_name} se try karein: {idea}" if lang == "hi" else f"Try making: {idea}"
            return jsonify({"reply": reply, "intent": intent, "success": True})

        reply = "Mujhe is item ke liye recipe nahi mili." if lang == "hi" else "I couldn't find a recipe for that item."
        return jsonify({"reply": reply, "intent": intent, "success": False})

    # ── UNKNOWN ───────────────────────────────────────────────────────────
    reply = "Samajh nahi paya, dobara try karein." if lang == "hi" else "Sorry, I didn't understand that. Please try again."
    return jsonify({"reply": reply, "intent": "unknown", "success": False})


# ── SETTINGS ─────────────────────────────────────────────────────────────────

@app.route("/settings")
@login_required
def settings():
    lang = get_lang()
    T = TRANSLATIONS[lang]
    username = session.get('username')
    user_data = db_get_user(username) or {
        'username': username,
        'full_name': username.capitalize() if username else '',
        'email': '',
        'created_at': 'Unknown',
        'updated_at': 'Never'
    }
    user_products = db_get_products(session.get('user_id'))
    return render_template("settings.html",
                           user=user_data,
                           products_count=len(user_products),
                           lang=lang, T=T, TRANSLATIONS=TRANSLATIONS)

@app.route("/settings/change-password", methods=["POST"])
@login_required
def change_password():
    lang = get_lang()
    T = TRANSLATIONS[lang]
    username = session.get('username')
    current_password = request.form.get("current_password", "").strip()
    new_password = request.form.get("new_password", "").strip()
    confirm_password = request.form.get("confirm_password", "").strip()

    user = db_get_user(username)
    if not user or user["password"] != hash_password(current_password):
        flash("error|Current password is incorrect!")
        return redirect(url_for("profile", tab=request.form.get("tab", "overview")))

    if new_password != confirm_password:
        flash("error|New passwords do not match!")
        return redirect(url_for("profile", tab=request.form.get("tab", "overview")))

    is_valid, password_msg = validate_password(new_password)
    if not is_valid:
        flash(f"error|{password_msg}")
        return redirect(url_for("profile", tab=request.form.get("tab", "overview")))

    db_update_user(username, {
        "password": hash_password(new_password),
        "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    })
    flash("success|Password changed successfully!")
    return redirect(url_for("profile", tab=request.form.get("tab", "overview")))

@app.route("/toggle-theme")
@login_required
def toggle_theme():
    current_theme = session.get('theme', 'dark')
    new_theme = 'dark' if current_theme == 'light' else 'light'
    session['theme'] = new_theme
    lang = get_lang()
    T = TRANSLATIONS[lang]
    flash(f"success|{T.get('theme_changed', 'Theme changed successfully!')}")
    return redirect(request.referrer or url_for('settings'))

@app.route("/settings/theme", methods=["POST"])
@login_required
def update_theme():
    theme = request.form.get('theme', 'dark')
    if theme in ['light', 'dark']:
        session['theme'] = theme
        username = session.get('username')
        if username:
            db_update_user(username, {"theme": theme})
    lang = get_lang()
    T = TRANSLATIONS[lang]
    flash(f"success|{T.get('theme_changed', 'Theme changed successfully!')}")
    return redirect(url_for('profile', tab=request.form.get('tab', 'overview')))

@app.route("/settings/language", methods=["POST"])
@login_required
def update_language():
    language = request.form.get('language', 'en')
    if language in ['en', 'hi']:   # Only en and hi
        session['lang'] = language
    lang = get_lang()
    T = TRANSLATIONS[lang]
    flash(f"success|{T.get('language_changed', 'Language changed successfully!')}")
    return redirect(url_for('profile', tab=request.form.get('tab', 'overview')))

@app.route("/settings/notifications", methods=["POST"])
@login_required
def update_notifications():
    session['expiry_alerts'] = request.form.get('expiry_alerts') == 'on'
    session['daily_reminders'] = request.form.get('daily_reminders') == 'on'
    session['email_notifications'] = request.form.get('email_notifications') == 'on'
    lang = get_lang()
    T = TRANSLATIONS[lang]
    flash(f"success|{T.get('notification_preferences_updated', 'Notification preferences updated!')}")
    return redirect(url_for('profile', tab=request.form.get('tab', 'overview')))

@app.route("/settings/feedback", methods=["POST"])
@login_required
def submit_feedback():
    feedback = request.form.get('feedback', '').strip()
    rating = request.form.get('rating', '5')
    if feedback:
        print(f"Feedback from {session.get('username')}: Rating={rating}, Feedback={feedback}")
    lang = get_lang()
    T = TRANSLATIONS[lang]
    flash(f"success|{T.get('feedback_sent', 'Feedback sent successfully!')}")
    return redirect(url_for('profile', tab=request.form.get('tab', 'overview')))

@app.route("/settings/export-data")
@login_required
def export_data():
    user_products = db_get_products(session.get('user_id'))
    data = json.dumps(user_products, indent=2, default=str)
    lang = get_lang()
    T = TRANSLATIONS[lang]
    flash(f"success|{T.get('data_exported', 'Data exported successfully!')}")
    return Response(
        data,
        mimetype="application/json",
        headers={"Content-Disposition": "attachment;filename=products_data.json"}
    )

@app.route("/settings/clear-data", methods=["POST"])
@login_required
def clear_data():
    db_clear_user_products(session.get('user_id'))
    lang = get_lang()
    T = TRANSLATIONS[lang]
    flash(f"success|{T.get('data_cleared', 'All data cleared successfully!')}")
    return redirect(url_for('profile', tab=request.form.get('tab', 'overview')))

@app.route("/settings/delete-account", methods=["POST"])
@login_required
def delete_account():
    lang = get_lang()
    T = TRANSLATIONS[lang]
    username = session.get('username')
    confirm_password = request.form.get("confirm_password", "").strip()

    user = db_get_user(username)
    if not user or user["password"] != hash_password(confirm_password):
        flash(f"error|{T.get('incorrect_password', 'Incorrect password. Account was not deleted.')}")
        return redirect(url_for('profile', tab=request.form.get('tab', 'overview')))

    db_delete_user(username)
    db_clear_user_products(user.get('id'))

    session.clear()
    flash(f"success|{T.get('account_deleted', 'Your account has been permanently deleted.')}")
    return redirect(url_for('login'))

@app.route("/settings/upload-avatar", methods=["POST"])
@login_required
def upload_avatar():
    lang = get_lang()
    T = TRANSLATIONS[lang]
    username = session.get('username')
    file = request.files.get('avatar')

    if not file or file.filename == "":
        flash(f"error|{T.get('no_file_selected', 'No file selected.')}")
        return redirect(url_for('profile', tab=request.form.get('tab', 'overview')))

    allowed_ext = {'.png', '.jpg', '.jpeg', '.gif', '.webp'}
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in allowed_ext:
        flash(f"error|{T.get('invalid_image_type', 'Please upload a PNG, JPG, GIF or WEBP image.')}")
        return redirect(url_for('profile', tab=request.form.get('tab', 'overview')))

    file_bytes = file.read()
    if len(file_bytes) > 2 * 1024 * 1024:  # 2 MB limit
        flash(f"error|{T.get('image_too_large', 'Image is too large. Please upload an image under 2MB.')}")
        return redirect(url_for('profile', tab=request.form.get('tab', 'overview')))

    mime_map = {'.png': 'image/png', '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg',
                '.gif': 'image/gif', '.webp': 'image/webp'}
    b64 = base64.b64encode(file_bytes).decode('utf-8')
    data_uri = f"data:{mime_map[ext]};base64,{b64}"

    db_update_user(username, {"avatar": data_uri})
    flash(f"success|{T.get('avatar_updated', 'Profile picture updated successfully!')}")
    return redirect(url_for('profile', tab=request.form.get('tab', 'overview')))

@app.route("/settings/remove-avatar", methods=["POST"])
@login_required
def remove_avatar():
    lang = get_lang()
    T = TRANSLATIONS[lang]
    username = session.get('username')
    db_update_user(username, {"avatar": None})
    flash(f"success|{T.get('avatar_removed', 'Profile picture removed.')}")
    return redirect(url_for('profile', tab=request.form.get('tab', 'overview')))

@app.route("/settings/update-regional", methods=["POST"])
@login_required
def update_regional():
    lang = get_lang()
    T = TRANSLATIONS[lang]
    username = session.get('username')
    timezone = request.form.get("timezone", "Asia/Kolkata")
    date_format = request.form.get("date_format", "DD/MM/YYYY")
    db_update_user(username, {"timezone": timezone, "date_format": date_format})
    flash(f"success|{T.get('regional_updated', 'Regional preferences updated!')}")
    return redirect(url_for('profile', tab=request.form.get('tab', 'overview')))
    
if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5000))
    app.run(
        host='0.0.0.0',
        port=port,
        debug=False
    )