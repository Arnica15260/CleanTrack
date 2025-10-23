# admin_site_flow.py
# Requires: selenium, Chrome + chromedriver on PATH

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, ElementClickInterceptedException, StaleElementReferenceException
import time
from urllib.parse import urljoin

# ---- CONFIG ----
BASE = "http://127.0.0.1:8000"
LOGIN_URL = urljoin(BASE, "/users/login/")   # normal site login page
ADMIN_USER = "Arnica"                        # superuser/staff username (or email if your form uses email)
ADMIN_PASS = "12345"                         # superuser password

WAIT        = 12
AFTER_CLICK = 0.5
HILITE_MS   = 140

# Slow navigation pacing (no scrolling)
NAV_DELAY_BEFORE = 1.0  # pause before opening each header link
NAV_DELAY_AFTER  = 5.0   # pause after the page loads, before returning home

# If your login form uses "email" instead of "username", set this True
PREFER_EMAIL_FIELD = False

# ---- UTILS ----
def log(msg): print(msg, flush=True)

def wait_body(d, timeout=WAIT):
    WebDriverWait(d, timeout).until(EC.presence_of_element_located((By.TAG_NAME, "body")))

def highlight(d, el):
    try:
        d.execute_script("arguments[0].scrollIntoView({block:'center'});", el)
        orig = el.get_attribute("style") or ""
        d.execute_script(
            "arguments[0].setAttribute('style', arguments[1]);",
            el, orig + "; outline:2px solid #24a0ed; outline-offset:2px;"
        )
        time.sleep(HILITE_MS/1000)
        d.execute_script("arguments[0].setAttribute('style', arguments[1]);", el, orig)
    except Exception:
        pass

def safe_click(d, el, desc="element"):
    try:
        highlight(d, el); el.click(); time.sleep(AFTER_CLICK); log(f"🖱️ Clicked: {desc}"); return True
    except ElementClickInterceptedException:
        try:
            d.execute_script("arguments[0].scrollIntoView({block:'center'});", el)
            time.sleep(0.15); highlight(d, el); el.click()
            time.sleep(AFTER_CLICK); log(f"🖱️ Clicked (after scroll): {desc}"); return True
        except Exception:
            try:
                d.execute_script("arguments[0].click();", el)
                time.sleep(AFTER_CLICK); log(f"🖱️ Clicked (JS): {desc}"); return True
            except Exception:
                log(f"⚠️ Could not click: {desc}"); return False
    except StaleElementReferenceException:
        log(f"↻ Stale on click: {desc}"); return False
    except Exception:
        try:
            d.execute_script("arguments[0].click();", el)
            time.sleep(AFTER_CLICK); log(f"🖱️ Clicked (JS): {desc}"); return True
        except Exception:
            log(f"⚠️ Could not click: {desc}"); return False

def click_and_log(d, by, sel, desc, timeout=WAIT):
    try:
        el = WebDriverWait(d, timeout).until(EC.element_to_be_clickable((by, sel)))
        return safe_click(d, el, desc)
    except TimeoutException:
        log(f"⚠️ Not found/clickable: {desc} ({sel})"); return False

def find_first(d, locators, timeout=WAIT):
    for by, sel in locators:
        try:
            return WebDriverWait(d, timeout).until(EC.presence_of_element_located((by, sel)))
        except TimeoutException:
            continue
    return None

def collect_header_hrefs(d):
    """Collect header/nav links (top area) as HREFs to avoid stale elements."""
    hrefs = []
    elems = d.find_elements(By.CSS_SELECTOR, "header a, nav a, .navbar a, .nav-link, .nav-item a")
    for el in elems:
        try:
            href = el.get_attribute("href")
            label = (el.text or "").strip()
            if not href:
                continue
            if href.endswith("#") or href.lower().startswith("javascript:"):
                continue
            hrefs.append((href, label))
        except Exception:
            continue
    # de-dup while preserving order
    seen = set(); uniq = []
    for h, t in hrefs:
        if h in seen: continue
        seen.add(h); uniq.append((h, t))
    return uniq

# ---- TEST FLOW ----
d = webdriver.Chrome()
d.maximize_window()

try:
    # 0) Normal site login page (NOT /admin/)
    d.get(LOGIN_URL); wait_body(d)

    # Try common login field variants
    if PREFER_EMAIL_FIELD:
        login_field = find_first(d, [
            (By.NAME, "email"),
            (By.CSS_SELECTOR, "input[type='email']"),
            (By.NAME, "username"),  # fallback
        ])
    else:
        login_field = find_first(d, [
            (By.NAME, "username"),
            (By.NAME, "email"),
            (By.CSS_SELECTOR, "input[type='email']"),
        ])
    if not login_field:
        raise RuntimeError("Login field (username/email) not found on normal login page.")

    login_field.clear()
    login_field.send_keys(ADMIN_USER)

    pwd_field = find_first(d, [
        (By.NAME, "password"),
        (By.CSS_SELECTOR, "input[type='password']"),
        (By.ID, "id_password"),
    ])
    if not pwd_field:
        raise RuntimeError("Password field not found on normal login page.")
    pwd_field.clear()
    pwd_field.send_keys(ADMIN_PASS)

    # Submit the form
    clicked = (
        click_and_log(d, By.XPATH, "//button[contains(.,'Log in') or contains(.,'Login') or @type='submit']",
                      "Site Login") or
        click_and_log(d, By.CSS_SELECTOR, "form button[type='submit']", "Site Login submit")
    )
    if not clicked:
        d.execute_script("var f=document.querySelector('form'); if(f) f.submit();")
        log("🖱️ Submitted normal login via JS form.submit()")

    # Wait for signed-in state
    try:
        WebDriverWait(d, WAIT).until(
            lambda drv: "/dashboard" in drv.current_url
                        or len(drv.find_elements(By.XPATH, "//a[contains(.,'Logout') or contains(.,'Log out')]")) > 0
        )
    except TimeoutException:
        pass

    log(f"✅ Logged in via normal page — URL: {d.current_url}")

    # 1) Open Django Admin with same session
    admin_url = urljoin(BASE, "/admin/")
    d.get(admin_url); wait_body(d)

    # If admin login prompts again, fill it
    if d.find_elements(By.NAME, "username") and d.find_elements(By.NAME, "password") and "Log in" in d.page_source:
        log("ℹ️ Admin login prompt shown — filling admin credentials.")
        WebDriverWait(d, WAIT).until(EC.presence_of_element_located((By.NAME, "username"))).clear()
        d.find_element(By.NAME, "username").send_keys(ADMIN_USER)
        d.find_element(By.NAME, "password").clear()
        d.find_element(By.NAME, "password").send_keys(ADMIN_PASS)
        click_and_log(d, By.XPATH, "//input[@type='submit' or @value='Log in' or @value='Log In']",
                      "Admin Log in")

    # Verify admin dashboard loaded
    WebDriverWait(d, WAIT).until(
        EC.any_of(
            EC.presence_of_element_located((By.ID, "content-main")),
            EC.presence_of_element_located((By.CSS_SELECTOR, "#site-name, .dashboard-module, .app-list"))
        )
    )
    log("✅ Django Admin dashboard loaded.")

    # 2) Back to Home (no page scrolling)
    home_url = urljoin(BASE, "/")
    d.get(home_url); wait_body(d)
    log("🏠 Home loaded (no scrolling).")

    # 3) Navigate header links SLOWLY (no scrolling — just paced nav)
    header_links = collect_header_hrefs(d)
    if not header_links:
        log("⚠️ No header links found.")
    for href, label in header_links:
        time.sleep(NAV_DELAY_BEFORE)
        d.get(href); wait_body(d)
        log(f"🧭 Navigated: {href} {'('+label+')' if label else ''}")
        time.sleep(NAV_DELAY_AFTER)
        d.get(home_url); wait_body(d)

    log("✅ Header navigation completed (slow-paced, no scrolling).")




finally:
    time.sleep(0.4)
    d.quit()
    log("🚪 Browser closed — admin test finished.")
