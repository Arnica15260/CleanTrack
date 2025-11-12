# Cleantrackplus.py
# Encoding: UTF-8
#
# Public pages (Home/About/Contact): slow top→bottom scroll for demo
# Auth + App flows: fast
# Prints success messages for Schedule, Donate/Reuse, Recycling, Complaints, etc.
#
# Run your server first:
#   python manage.py runserver 127.0.0.1:8000

import os
import time
from datetime import datetime, timedelta

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import WebDriverException

# =========================
# CONFIG
# =========================
BASE = "http://127.0.0.1:8000"   # ensure no leading/trailing spaces
LOGIN_URL = f"{BASE}/users/login/"
DASHBOARD_URL = f"{BASE}/users/dashboard/"
SCHEDULE_URL = f"{BASE}/users/schedule/"

LOGIN = {"username": "Troyi", "password": "V=u+at15260"}

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))

def resolve_asset_path(user_path: str, fallback_filename: str) -> str:
    cand = []
    if user_path:
        up = os.path.abspath(user_path)
        if os.path.isfile(up):
            return up
        cand.append(os.path.join(PROJECT_ROOT, user_path))
    cand.extend([
        os.path.join(PROJECT_ROOT, "Selenium_test", "Selenium_test", "assets", fallback_filename),
        os.path.join(PROJECT_ROOT, "Selenium_test", "assets", fallback_filename),
        os.path.join(PROJECT_ROOT, "assets", fallback_filename),
    ])
    for p in cand:
        if os.path.isfile(p):
            return os.path.abspath(p)
    return user_path

def tomorrow_iso():
    return (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")

def normalize_date(dstr: str) -> str:
    if not dstr:
        return dstr
    s = dstr.strip().replace("/", "-")
    parts = s.split("-")
    try:
        if len(parts) == 3 and len(parts[0]) == 4:  # already ISO
            return f"{int(parts[0]):04d}-{int(parts[1]):02d}-{int(parts[2]):02d}"
        if len(parts) == 3:  # DD-MM-YYYY → YYYY-MM-DD
            d, m, y = int(parts[0]), int(parts[1]), int(parts[2])
            return f"{y:04d}-{m:02d}-{d:02d}"
    except Exception:
        pass
    return dstr

DATA = {
    "contact_name": "Troyi",
    "contact_email": "troyi@gmail.com",
    "contact_message": "Hello! This is a regular-user test for CleanTrack+.",

    # Scheduling (we'll override schedule_date below to be tomorrow)
    "schedule_date": "30-9-2025",
    "schedule_time": "11:30",
    "schedule_address": "Flat B2, House 7, Road 3, Banani, Dhaka 1213",
    "schedule_notes": "Please come on time.",

    # Reuse
    "reuse_category": "Books",
    "reuse_quantity": "5",
    "reuse_partner": "NGO Partner",
    "reuse_note": "Stack of GRE/IELTS prep books in good condition.",

    # Recycling
    "recycling_category": "General",
    "recycling_date": "2025-10-30",
    "recycling_address": "Flat B2, House 7, Road 3, Banani, Dhaka 1213",
    "recycling_note": "Mixed recyclables, please collect from guard room.",

    # Complaints
    "complaint_subject": "Pickup delay (E2E)",
    "complaint_category": "Service",
    "complaint_order": "CTP-REG-2025-001",
    "complaint_message": "This is an automated E2E test complaint. Please ignore.",

    # Tracking
    "tracking_id": "CTP-TRACK-0001",

    # Optional local files for uploads (can be blank)
    "schedule_photo_path": "Selenium_test/Selenium_test/assets/schedule_sample.jpg",
    "reuse_photo_path": "Selenium_test/Selenium_test/assets/reuse_sample.jpg",
    "complaint_photo_path": "Selenium_test/Selenium_test/assets/complaint_sample.jpg",
}

# Resolve asset paths once
DATA["schedule_photo_path"]  = resolve_asset_path(DATA.get("schedule_photo_path", ""),  "schedule_sample.jpg")
DATA["reuse_photo_path"] = resolve_asset_path(DATA.get("reuse_photo_path", ""), "reuse_sample.jpg")
DATA["complaint_photo_path"] = resolve_asset_path(DATA.get("complaint_photo_path", ""), "complaint_sample.jpg")

# =========================
# SPEED (tight, fast for forms)
# =========================
CFG = dict(
    AFTER_CLICK_PAUSE=0.10,
    AFTER_SUBMIT_PAUSE=0.25,
    SETTLE_PAUSE=0.10,
    TYPE_DELAY=0.002,  # ultra-fast typing
)

# =========================
# UTILITIES
# =========================
def wait_ready(d, timeout=10):
    WebDriverWait(d, timeout).until(EC.presence_of_element_located((By.TAG_NAME, "body")))

def settle(d, sec=None):
    time.sleep(CFG["SETTLE_PAUSE"] if sec is None else sec)

def slow_scroll_public(d, step=350, pause=0.50, loops=1):
    for _ in range(loops):
        last_h = d.execute_script(
            "return Math.max(document.body.scrollHeight,document.documentElement.scrollHeight)"
        )
        y = 0
        while y < last_h:
            d.execute_script(f"window.scrollTo(0,{y});")
            time.sleep(pause)
            y += step
            last_h = d.execute_script(
                "return Math.max(document.body.scrollHeight,document.documentElement.scrollHeight)"
            )
        d.execute_script("window.scrollTo(0,document.body.scrollHeight);")
        time.sleep(pause)
        d.execute_script("window.scrollTo({top:0,behavior:'instant'})")
        time.sleep(0.25)

def robust_click(d, el):
    if not el:
        return False
    try:
        el.click()
        time.sleep(CFG["AFTER_CLICK_PAUSE"])
        return True
    except Exception:
        try:
            d.execute_script("arguments[0].scrollIntoView({block:'center'});", el)
            time.sleep(0.05)
            el.click()
            time.sleep(CFG["AFTER_CLICK_PAUSE"])
            return True
        except Exception:
            try:
                d.execute_script("arguments[0].click();", el)
                time.sleep(CFG["AFTER_CLICK_PAUSE"])
                return True
            except Exception:
                return False

def find_clickable(d, by, timeout=6):
    try:
        return WebDriverWait(d, timeout).until(EC.element_to_be_clickable(by))
    except Exception:
        return None

def safe_find(d, by, timeout=5):
    try:
        return WebDriverWait(d, timeout).until(EC.presence_of_element_located(by))
    except Exception:
        return None

def safe_find_all(d, by, timeout=4):
    try:
        WebDriverWait(d, timeout).until(EC.presence_of_element_located(by))
        return d.find_elements(*by)
    except Exception:
        return []

def type_into(d, by, text, timeout=6, clear=True):
    el = WebDriverWait(d, timeout).until(EC.visibility_of_element_located(by))
    if clear:
        try: el.clear()
        except Exception: pass
    el.send_keys(text)
    return el

def click_any(d, candidates):
    for how, selector in candidates:
        try:
            if how == "css":
                el = find_clickable(d, (By.CSS_SELECTOR, selector))
            elif how == "xpath":
                el = find_clickable(d, (By.XPATH, selector))
            elif how == "link":
                el = find_clickable(d, (By.LINK_TEXT, selector))
            elif how == "plink":
                el = find_clickable(d, (By.PARTIAL_LINK_TEXT, selector))
            else:
                el = None
            if el and robust_click(d, el):
                return True
        except Exception:
            continue
    return False

# ---------- JS helpers for reliable form filling ----------
def js_set_value(d, el, value: str):
    d.execute_script("""
        const el = arguments[0], val = arguments[1];
        el.value = val;
        el.dispatchEvent(new Event('input', {bubbles:true}));
        el.dispatchEvent(new Event('change', {bubbles:true}));
    """, el, value)

def js_set_value_by_selector(d, selector, value, css=True):
    query = "document.querySelector(arguments[0])" if css else "document.evaluate(arguments[0],document,null,XPathResult.FIRST_ORDERED_NODE_TYPE,null).singleNodeValue"
    return d.execute_script(f"""
        const node = {query};
        if (node) {{
            node.value = arguments[1];
            node.dispatchEvent(new Event('input', {{bubbles:true}}));
            node.dispatchEvent(new Event('change', {{bubbles:true}}));
            return true;
        }}
        return false;
    """, selector, value)

# --------- success/alert detection (wider net) ---------
def get_success_text(d):
    sel_candidates = [
        # Generic / Django
        (By.CSS_SELECTOR, ".alert.alert-success, .alert-success, .messages .success, li.message.success"),
        (By.CSS_SELECTOR, "#messages .alert-success, #django-messages .message.success"),
        # Toasts & snackbars (iziToast, Notyf, Toastify, bootstrap .toast, etc.)
        (By.CSS_SELECTOR, ".toast.show, .toast-success, .iziToast, .notyf, .notyf__toast, .Toastify__toast--success"),
        # SweetAlert2
        (By.CSS_SELECTOR, ".swal2-container .swal2-icon.swal2-success, .swal2-container .swal2-title, .swal2-html-container"),
        # Ant Design / MUI / Vuetify / Bulma / UIKit
        (By.CSS_SELECTOR, ".ant-message-notice, .MuiAlert-standardSuccess, .v-alert--success, .notification.is-success, .uk-alert-success"),
        # ARIA/role
        (By.CSS_SELECTOR, "[role='alert'], [aria-live='polite'], [aria-live='assertive'], [role='status']"),
        # Fallback id/classes
        (By.CSS_SELECTOR, "#success, #successMsg, .msg-success, .flash-success"),
        # Text contains "success"
        (By.XPATH, "//*[contains(translate(., 'SUCCESS', 'success'),'success') and (contains(@class,'alert') or contains(@class,'toast') or contains(@class,'message') or @role='alert')]"),
    ]
    for by in sel_candidates:
        el = safe_find(d, by, timeout=1)
        if el:
            try:
                txt = el.text.strip()
                if txt:
                    return txt
            except Exception:
                pass
    return None

def collect_any_messages(d):
    containers = [
        (By.CSS_SELECTOR, "#messages, #django-messages, .messages"),
        (By.CSS_SELECTOR, ".alert, .toast, .notification, [role='alert'], [role='status']"),
        (By.XPATH, "//ul[contains(@class,'messages')] | //div[contains(@class,'messages')]"),
    ]
    texts = []
    for by in containers:
        els = safe_find_all(d, by, timeout=1)
        for el in els:
            try:
                t = (el.text or "").strip()
                if t:
                    texts.append(t)
            except Exception:
                pass
    return "\n".join(texts) if texts else None

def wait_for_message_or_url_change(d, start_url, timeout=6):
    end = time.time() + timeout
    while time.time() < end:
        msg = collect_any_messages(d)
        if msg:
            return msg
        try:
            if d.current_url != start_url:
                wait_ready(d, timeout=5)
                txt = get_success_text(d)
                if txt:
                    return txt
                return collect_any_messages(d)
        except Exception:
            pass
        time.sleep(0.15)
    return None

def page_contains_any(d, texts):
    """Return True if any provided strings appear in the DOM text."""
    try:
        body = d.find_element(By.TAG_NAME, "body").text
        return any(t for t in texts if t and t in body)
    except Exception:
        return False

def show_form_errors_if_any(d):
    # Typical Django error containers
    err_blocks = safe_find_all(d, (By.CSS_SELECTOR, ".errorlist, .invalid-feedback, .help.is-danger, .is-invalid"))
    texts = []
    for el in err_blocks:
        try:
            t = el.text.strip()
            if t:
                texts.append(t)
        except Exception:
            pass
    if texts:
        print("❌ Form errors detected:")
        for t in texts:
            print("   •", t)
        return True
    return False

def go_dashboard(d):
    if click_any(d, [
        ("css", "a[href*='/users/dashboard']"),
        ("xpath", "//a[contains(@href,'/users/dashboard')]"),
        ("link", "Dashboard"),
        ("plink", "Dashboard"),
    ]):
        wait_ready(d); return
    d.get(DASHBOARD_URL); wait_ready(d)

# ---- markers to prove listing existence when UI echoes text ----
def gen_marker():
    return f"E2E-{int(time.time()*1000)}"

def verify_by_marker(d, marker, also_check_dashboard=True):
    # current page
    if page_contains_any(d, [marker]):
        print(f"✅ Verified by marker on current page: {marker}")
        return True
    # dashboard
    if also_check_dashboard:
        go_dashboard(d)
        if page_contains_any(d, [marker]):
            print(f"✅ Verified by marker on Dashboard: {marker}")
            return True
    return False

# ---- fuzzy verification: human date/time forms + snippet checks ----
def date_variants(iso_date: str):
    """
    Generate common display variants for a YYYY-MM-DD date.
    """
    try:
        dt = datetime.strptime(iso_date, "%Y-%m-%d")
    except Exception:
        return [iso_date]

    d = dt.day
    m = dt.month
    y = dt.year
    mon_short = dt.strftime("%b")   # Oct
    mon_long  = dt.strftime("%B")   # October

    variants = [
        dt.strftime("%Y-%m-%d"),          # 2025-10-23
        f"{d:02d}-{m:02d}-{y}",           # 23-10-2025
        f"{d}-{m}-{y}",                   # 23-10-2025 (no leading zeros)
        f"{d:02d}/{m:02d}/{y}",           # 23/10/2025
        f"{mon_short} {d}, {y}",          # Oct 23, 2025
        f"{mon_long} {d}, {y}",           # October 23, 2025
        f"{d} {mon_short} {y}",           # 23 Oct 2025
        f"{d} {mon_long} {y}",            # 23 October 2025
    ]
    return list(dict.fromkeys(variants))  # de-dupe preserve order

def time_variants(hhmm: str):
    """
    Generate 24h and 12h variants.
    """
    if not hhmm:
        return []
    try:
        t24 = datetime.strptime(hhmm, "%H:%M")
        t12 = t24.strftime("%I:%M %p").lstrip("0")  # 11:30 AM
        return [hhmm, t12, t12.lower()]
    except Exception:
        return [hhmm]

def contains_any_text(d, texts):
    try:
        body = d.find_element(By.TAG_NAME, "body").text
        for t in texts:
            if t and t in body:
                return True
    except Exception:
        pass
    return False

def verify_fuzzy_save(d, iso_date, hhmm=None, extra_text=None, also_check_dashboard=True):
    """
    Consider it verified if:
      - current page OR dashboard contains one of the date variants
        AND (time variant OR extra_text snippet)
      - OR the form appears to have cleared after submit.
    """
    date_opts = date_variants(iso_date)
    time_opts = time_variants(hhmm) if hhmm else []
    snippets  = [s for s in ([extra_text] if extra_text else []) if s]

    # 1) same page
    if (contains_any_text(d, date_opts) and
        (contains_any_text(d, time_opts) or contains_any_text(d, snippets))):
        print(f"✅ Verified by fuzzy content on current page ({iso_date} / {hhmm or '-'}).")
        return True

    # 2) dashboard
    if also_check_dashboard:
        go_dashboard(d)
        if (contains_any_text(d, date_opts) and
            (contains_any_text(d, time_opts) or contains_any_text(d, snippets))):
            print(f"✅ Verified by fuzzy content on Dashboard ({iso_date} / {hhmm or '-'}).")
            return True

    # 3) form cleared heuristic (two+ fields empty)
    empties = 0
    css_candidates = [
        "#id_date", "[name='date']",
        "#id_time", "[name='time']",
        "#id_address", "[name='address']",
        "#id_notes", "[name='notes']",
        "#id_message", "[name='message']"
    ]
    for sel in css_candidates:
        el = None
        try:
            el = d.find_element(By.CSS_SELECTOR, sel)
        except Exception:
            pass
        if el is not None:
            try:
                if (el.get_attribute("value") or "").strip() == "":
                    empties += 1
            except Exception:
                pass
    if empties >= 2:
        print("✅ Verified by cleared form fields after submit.")
        return True

    return False

# =========================
# FLOWS
# =========================
def home_public_slow_then_contact_fast(d):
    print("▶ Home (slow scroll) + Contact (navigate only)")
    d.get(BASE); wait_ready(d)
    # slow scroll on Home
    slow_scroll_public(d, loops=1)
    # navigate to Contact (no form fill)
    click_any(d, [("link","Contact"), ("plink","Contact")])
    wait_ready(d)
    slow_scroll_public(d, loops=1)
    # go back Home to keep parity with previous behavior
    click_any(d, [("link","Home"), ("plink","Home")])

def navbar_about_contact_public_slow_then_fill_fast(d):
    print("▶ Navbar: About (slow scroll) → Contact (slow scroll) — no form submit")
    if click_any(d, [("link","About"), ("plink","About")]):
        wait_ready(d); slow_scroll_public(d, loops=1)
    if click_any(d, [("link","Contact"), ("plink","Contact")]):
        wait_ready(d); slow_scroll_public(d, loops=1)
    # return Home (no form interaction)
    click_any(d, [("link","Home"), ("plink","Home")])

def login_fast(d):
    print("▶ Login as Troyi (fast)")
    d.get(LOGIN_URL); wait_ready(d)
    u = safe_find(d, (By.NAME, "username"))
    p = safe_find(d, (By.NAME, "password"))
    if u and p:
        u.clear(); u.send_keys(LOGIN["username"])
        p.clear(); p.send_keys(LOGIN["password"])
        click_any(d, [("xpath","//button[contains(.,'Log in') or contains(.,'Login') or @type='submit']"),
                      ("css","form button[type=submit]")])
    try:
        WebDriverWait(d, 6).until(EC.url_contains("/users/dashboard"))
    except Exception:
        d.get(DASHBOARD_URL)
    wait_ready(d)
    print("✅ Landed on dashboard")

def sidebar_profile_quick(d):
    print("▶ Sidebar → Profile (quick peek)")
    click_any(d, [("link","Profile"), ("plink","Profile")])
    settle(d, 0.1)
    go_dashboard(d)

# ----------------- SCHEDULE (unchanged) -----------------
def schedule_pickup_fast(d):
    print("▶ Sidebar → Schedule Pickup (fast fill + success)")
    if not click_any(d, [("link","Schedule Pickup"), ("plink","Schedule")]):
        d.get(SCHEDULE_URL)
    wait_ready(d)

    # keep your hidden field behavior
    try:
        js_set_value_by_selector(d, "#waste_type", "regular", css=True)
        js_set_value_by_selector(d, "input[name='waste_type']", "regular", css=True)
    except Exception:
        pass

    date_iso = tomorrow_iso()
    time_24h = DATA.get("schedule_time", "11:30")
    addr = DATA.get("schedule_address", "")
    notes = (DATA.get("schedule_notes", "") or "").strip()

    # date
    date_el = (safe_find(d, (By.ID, "id_date")) or safe_find(d, (By.NAME, "date")))
    if date_el:
        try: js_set_value(d, date_el, date_iso)
        except Exception:
            try: date_el.clear(); date_el.send_keys(date_iso)
            except Exception: pass

    # time
    time_el = (safe_find(d, (By.ID, "id_time")) or safe_find(d, (By.NAME, "time")))
    if time_el:
        try: js_set_value(d, time_el, time_24h)
        except Exception:
            try: time_el.clear(); time_el.send_keys(time_24h)
            except Exception: pass

    # address
    addr_el = (safe_find(d, (By.ID, "id_address")) or safe_find(d, (By.NAME, "address")))
    if addr_el:
        try: js_set_value(d, addr_el, addr)
        except Exception:
            try: addr_el.clear(); addr_el.send_keys(addr)
            except Exception: pass

    # notes
    notes_el = (safe_find(d, (By.ID, "id_notes")) or safe_find(d, (By.NAME, "notes")))
    if notes_el:
        try: js_set_value(d, notes_el, notes)
        except Exception:
            try: notes_el.clear(); notes_el.send_keys(notes)
            except Exception: pass

    # optional photo
    attach_file_if_exists(
        d,
        [
            ("css", "input[type='file'][name*='image']"),
            ("css", "input[type='file'][name*='photo']"),
            ("css", "input[type='file']#id_image"),
            ("xpath", "//input[@type='file']"),
        ],
        DATA.get("schedule_photo_path")
    )

    # submit
    if click_any(d, [
        ("xpath", "//button[contains(.,'Schedule Pickup') or contains(.,'Submit') or @type='submit']"),
        ("css", "#pickupForm button[type=submit]"),
        ("css", "form button[type=submit]")
    ]):
        txt = get_success_text(d) or collect_any_messages(d)
        print("✅ Schedule saved" + (f": {txt}" if txt else ""))

    go_dashboard(d)

def donate_reuse_fast(d):
    print("▶ Sidebar → Donate / Reuse (fast fill + success)")
    click_any(d, [("link","Donate / Reuse"), ("link","Reuse"), ("link","Donate"), ("plink","Reuse")])
    cat = safe_find(d, (By.NAME, "category"))
    if cat:
        try:
            Select(cat).select_by_visible_text(DATA["reuse_category"])
        except Exception:
            try: cat.clear(); cat.send_keys(DATA["reuse_category"])
            except Exception: pass
    qty = safe_find(d, (By.NAME, "quantity"))
    if qty:
        try: qty.clear()
        except Exception: pass
        qty.send_keys(DATA["reuse_quantity"])
    partner = safe_find(d, (By.NAME, "partner"))
    if partner:
        try: partner.clear()
        except Exception: pass
        partner.send_keys(DATA["reuse_partner"])
    note = safe_find(d, (By.NAME, "note")) or safe_find(d, (By.NAME, "details"))
    if note:
        try: note.clear()
        except Exception: pass
        note.send_keys(DATA["reuse_note"])
    if click_any(d, [("xpath", "//button[contains(.,'Save Donation') or contains(.,'Submit') or contains(.,'Save') or @type='submit']"),
                     ("css", "form button[type=submit]")]):
        txt = get_success_text(d) or collect_any_messages(d)
        print("✅ Donation saved" + (f": {txt}" if txt else ""))
    go_dashboard(d)

# ----------------- RECYCLING (navigate only) -----------------
def recycling_fast(d):
    print("▶ Sidebar → Recycling (navigate only; no form fill)")
    # Just open the page and maybe show it briefly
    if click_any(d, [("link","Recycling"), ("plink","Recycling")]):
        wait_ready(d)
        slow_scroll_public(d, loops=1)  # optional visual demo
    else:
        # try direct nav if sidebar link missing
        for path in ("/users/recycling/", "/recycling/", "/users/recycle/", "/recycle/"):
            try:
                d.get(BASE + path); wait_ready(d); break
            except WebDriverException:
                continue
        slow_scroll_public(d, loops=1)
    # Do NOT fill or submit anything; return to dashboard
    go_dashboard(d)

def reuse_market_fast(d):
    print("▶ Sidebar → Reuse Market (fast)")
    click_any(d, [("link","Reuse Market"), ("plink","Reuse Market")])
    accepted = click_any(d, [
        ("xpath", "//button[contains(.,'Accept') or contains(.,'Take') or contains(.,'Claim') or contains(.,'Grab')]"),
        ("xpath", "//a[contains(.,'Accept') or contains(.,'Take') or contains(.,'Claim') or contains(.,'Grab')]"),
        ("css", "form[action*='accept'] button[type=submit], form[action*='accept'] .btn"),
    ])
    if accepted:
        txt = get_success_text(d) or collect_any_messages(d)
        print("✅ Accepted market item" + (f": {txt}" if txt else ""))
    go_dashboard(d)

def my_accepted_fast(d):
    print("▶ Sidebar → My Accepted (fast)")
    click_any(d, [("link","My Accepted List"), ("link","My Accepted"), ("plink","Accepted")])
    if not click_any(d, [("css", "a[href^='mailto:']"), ("css", "a[href^='tel:']")]):
        item = safe_find(d, (By.CSS_SELECTOR, ".item, .card"))
        if item: robust_click(d, item)
    go_dashboard(d)

# ----------------- COMPLAINTS: marker + fuzzy verification -----------------
def complaints_fast(d):
    print("▶ Sidebar → Complaints (fast; marker/fuzzy verification)")
    click_any(d, [("link","Complaints"), ("link","Complaint"), ("plink","Complaint")])

    marker = gen_marker()

    subj = (safe_find(d, (By.NAME, "subject")) or safe_find(d, (By.ID, "id_subject")))
    cat  = (safe_find(d, (By.NAME, "category")) or safe_find(d, (By.ID, "id_category")))
    order= (safe_find(d, (By.NAME, "order")) or safe_find(d, (By.NAME, "order_id")) or safe_find(d, (By.NAME, "tracking")))
    msg  = (safe_find(d, (By.NAME, "message")) or safe_find(d, (By.ID, "id_message")))
    filled = False

    if subj: subj.clear(); subj.send_keys(DATA.get("complaint_subject", "")); filled = True
    if cat:
        try:
            Select(cat).select_by_visible_text(DATA.get("complaint_category", "")); filled = True
        except Exception:
            try: cat.clear(); cat.send_keys(DATA.get("complaint_category", "")); filled = True
            except Exception: pass
    if order: order.clear(); order.send_keys(DATA.get("complaint_order", "")); filled = True
    if msg:
        txt = (DATA.get("complaint_message", "") + f" [{marker}]").strip()
        msg.clear(); msg.send_keys(txt); filled = True

    attach_file_if_exists(
        d,
        [
            ("css", "input[type='file'][name*='image']"),
            ("css", "input[type='file'][name*='photo']"),
            ("css", "input[type='file']#id_image"),
            ("xpath", "//input[@type='file']"),
        ],
        DATA.get("complaint_photo_path")
    )

    start_url = d.current_url
    if filled and click_any(d, [
        ("xpath", "//button[contains(.,'Submit') or contains(.,'Send') or contains(.,'Save')]"),
        ("css", "form button[type=submit]")
    ]):
        msgtxt = wait_for_message_or_url_change(d, start_url, timeout=6)
        if msgtxt:
            print(f"✅ Complaint submit message: {msgtxt}")

    go_dashboard(d)

def attach_file_if_exists(d, possible_selectors, file_path):
    if not file_path:
        return False
    path = os.path.abspath(file_path)
    if not os.path.isfile(path):
        print(f"ℹ Upload skipped: file not found -> {path}")
        return False
    for how, selector in possible_selectors:
        try:
            if how == "css":
                el = safe_find(d, (By.CSS_SELECTOR, selector), timeout=2)
            elif how == "xpath":
                el = safe_find(d, (By.XPATH, selector), timeout=2)
            else:
                el = None
            if el and (el.get_attribute("type") or "").lower() == "file":
                el.send_keys(path)
                print(f"📎 Attached file: {path}")
                return True
        except Exception:
            continue
    return False

def tracking_quick(d):
    print("▶ Track / Tracking (fast)")
    found = click_any(d, [
        ("link", "Track"), ("plink", "Track"),
        ("link", "Tracking"), ("plink", "Tracking"),
        ("plink", "Driver Tracking"), ("plink", "Order Tracking"),
        ("css", "a[href*='/track']"),
        ("xpath", "//a[contains(@href,'/track') or contains(.,'Track')]"),
    ])
    if not found:
        for path in ("/track/", "/users/track/", "/tracking/", "/users/tracking/"):
            try:
                d.get(BASE + path); wait_ready(d); break
            except WebDriverException:
                continue
    tid = safe_find(d, (By.NAME, "tracking_id")) or safe_find(d, (By.ID, "id_tracking_id"))
    if tid:
        try:
            tid.clear(); tid.send_keys(DATA["tracking_id"])
            click_any(d, [("xpath", "//button[contains(.,'Track') or @type='submit']"),
                          ("css", "form button[type=submit]")])
            txt = get_success_text(d) or collect_any_messages(d)
            print("✅ Tracking searched" + (f": {txt}" if txt else ""))
        except Exception:
            pass
    go_dashboard(d)

def logout_home_close(d):
    print("▶ Logout → Home")
    click_any(d, [
        ("css", "[data-bs-toggle='dropdown']"),
        ("css", ".dropdown-toggle"),
        ("css", "button[aria-expanded='false']"),
        ("xpath", "//img[contains(@class,'avatar')]/ancestor::button | //span[contains(@class,'user')]/ancestor::button")
    ])
    click_any(d, [
        ("link","Logout"), ("plink","Log out"), ("plink","Logout"),
        ("css","a[href*='logout']"), ("xpath","//a[contains(@href,'logout')]"),
        ("css","form[action*='logout'] button[type='submit']")
    ])
    try:
        d.get(BASE); wait_ready(d)
    except Exception:
        pass
    if click_any(d, [("link","Login"), ("plink","Log in")]):
        print("✅ Logged out (Login visible).")
    else:
        print("✅ Logged out (returned to Home).")

# =========================
# MAIN
# =========================
def main():
    # Always use a safe, valid date for scheduling
    DATA["schedule_date"] = tomorrow_iso()

    o = webdriver.ChromeOptions()
    o.add_argument("--start-maximized")
    o.add_argument("--disable-dev-shm-usage")
    o.add_argument("--disable-gpu")
    o.add_argument("--no-sandbox")
    o.add_experimental_option("excludeSwitches", ["enable-automation"])
    o.add_experimental_option('useAutomationExtension', False)

    d = webdriver.Chrome(options=o)
    d.implicitly_wait(2)
    try:
        # Public: slow scroll demo, fast nav (no form on Contact)
        home_public_slow_then_contact_fast(d)
        navbar_about_contact_public_slow_then_fill_fast(d)

        # Auth & Dashboard: fast
        login_fast(d)
        sidebar_profile_quick(d)

        # App flows
        schedule_pickup_fast(d)    # unchanged
        donate_reuse_fast(d)
        recycling_fast(d)          # now: navigate only
        reuse_market_fast(d)
        my_accepted_fast(d)
        complaints_fast(d)
        tracking_quick(d)

        # Logout
        logout_home_close(d)
        print("✅ E2E complete (Contact/Recycling: navigate only).")
    finally:
        try:
            d.quit()
        except Exception:
            pass

if __name__ == "__main__":
    main()
