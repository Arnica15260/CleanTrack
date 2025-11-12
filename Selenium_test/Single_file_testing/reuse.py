
import time
from pathlib import Path
from datetime import datetime
from urllib.parse import urlparse

from selenium import webdriver
from selenium.common.exceptions import TimeoutException, StaleElementReferenceException
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC


BASE          = " http://127.0.0.1:8000/"
LOGIN_URL     = f"{BASE}/users/login/"
DASHBOARD_URL = f"{BASE}/users/dashboard/"
REUSE_URL     = f"{BASE}/users/reuse/"
LOGOUT_URL    = f"{BASE}/users/logout/"


USERNAME = "Rahman"
PASSWORD = "V=u+at15260"

WAIT            = 20
STEP_PAUSE      = 0.9
TYPE_DELAY      = 0.035
HILITE_MS       = 250
RETRY_STALE_MAX = 2

SS_DIR = Path("../Selenium_test/screens"); SS_DIR.mkdir(parents=True, exist_ok=True)
ASSET_PHOTO = (Path.cwd() / "Selenium_test" / "assets" / "reuse_sample.jpg")  # optional image

def pause(*args, **kwargs):
    """pause() | pause(1.2) | pause("msg") | pause(1.2, "msg") | pause(sec=..., msg="...")"""
    sec = kwargs.get("sec", STEP_PAUSE)
    msg = kwargs.get("msg")
    if args:
        if isinstance(args[0], (int, float)):
            sec = args[0]
            if len(args) > 1 and isinstance(args[1], str):
                msg = args[1]
        elif isinstance(args[0], str):
            msg = args[0]
    if msg: print(msg)
    time.sleep(sec)

def ss(name):
    p = SS_DIR / f"{name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
    driver.save_screenshot(str(p)); print("📸", p)

def norm_path(url: str) -> str:
    p = urlparse(url); path = p.path or "/"
    return path[:-1] if len(path) > 1 and path.endswith("/") else path

def is_dash(url: str) -> bool:
    return norm_path(url).startswith("/users/dashboard")

def type_slow(el, text):
    try: el.clear()
    except Exception: pass
    for ch in str(text):
        el.send_keys(ch); time.sleep(TYPE_DELAY)

def highlight(el):
    driver.execute_script("arguments[0].scrollIntoView({block:'center'});", el)
    original = el.get_attribute("style") or ""
    driver.execute_script("arguments[0].setAttribute('style', arguments[1]);",
                          el, f"{original}; outline:2px solid #24a0ed; outline-offset:2px;")
    time.sleep(HILITE_MS/1000)
    driver.execute_script("arguments[0].setAttribute('style', arguments[1]);", el, original)

def click_one(by, locator, desc=""):
    for attempt in range(1, RETRY_STALE_MAX + 2):
        try:
            el = WebDriverWait(driver, WAIT).until(EC.element_to_be_clickable((by, locator)))
            highlight(el); el.click()
            if desc: print("🖱️ Clicked:", desc)
            pause()
            return True
        except StaleElementReferenceException:
            print(f"↻ Stale on {desc or locator} — retry {attempt}")
        except TimeoutException:
            return False
    return False

def click_any(locators, desc="", fallback_url=None):
    for by, loc in locators:
        if click_one(by, loc, desc): return True
    if fallback_url:
        print(f"⚠️ Couldn’t click {desc or 'target'}. Navigating to:", fallback_url)
        driver.get(fallback_url); pause()
        return True
    return False

def wait_toast_success():
    sels = [
        (By.CSS_SELECTOR, "#toast-stack .toast.success"),
        (By.CSS_SELECTOR, ".toast-stack .toast.success"),
        (By.XPATH, "//*[contains(@class,'toast') and contains(@class,'success')]"),
    ]
    for by, sel in sels:
        try:
            WebDriverWait(driver, 8).until(EC.presence_of_element_located((by, sel)))
            return True
        except TimeoutException:
            continue
    return False

def wait_logged_out():
    def _has_username():
        try:
            WebDriverWait(driver, 3).until(EC.visibility_of_element_located((By.NAME, "username"))); return True
        except TimeoutException:
            return False
    def _url_login():
        try:
            WebDriverWait(driver, 3).until(EC.url_contains("/users/login/")); return True
        except TimeoutException:
            return False
    def _has_login_link():
        try:
            WebDriverWait(driver, 3).until(EC.presence_of_element_located((By.XPATH, "//a[contains(@href,'/users/login/')]"))); return True
        except TimeoutException:
            return False
    def _no_logout_links():
        try:
            WebDriverWait(driver, 3).until_not(EC.presence_of_element_located((By.XPATH, "//a[contains(@href,'/users/logout/')]")))
            return True
        except TimeoutException:
            return False

    if _url_login() or _has_username() or _has_login_link() or _no_logout_links():
        return True
    driver.get(LOGIN_URL); pause(0.5)
    return _url_login() or _has_username() or _has_login_link() or _no_logout_links()


driver = webdriver.Chrome()
driver.set_window_size(1280, 900)

try:
    driver.get(LOGIN_URL); pause("➡️ Login page loaded")
    u = WebDriverWait(driver, WAIT).until(EC.visibility_of_element_located((By.NAME, "username")))
    print("⌨️ Typing username…"); type_slow(u, USERNAME); pause(0.25)
    p = WebDriverWait(driver, WAIT).until(EC.visibility_of_element_located((By.NAME, "password")))
    print("⌨️ Typing password…"); type_slow(p, PASSWORD); pause(0.25)
    form = u.find_element(By.XPATH, "ancestor::form"); highlight(form); form.submit(); print("🖱️ Submitted login form")

    try:
        WebDriverWait(driver, WAIT).until(lambda d: is_dash(d.current_url))
    except TimeoutException:
        driver.get(DASHBOARD_URL); WebDriverWait(driver, WAIT).until(lambda d: is_dash(d.current_url))
    print("➡️ Landed on Dashboard"); pause()


    click_any(
        [
            (By.XPATH, "//aside//a[contains(@href,'/users/reuse/')]"),
            (By.XPATH, "//a[contains(@href,'/users/reuse/')]"),
        ],
        desc="Reuse / Donate",
        fallback_url=REUSE_URL,
    )
    WebDriverWait(driver, WAIT).until(EC.url_contains("/users/reuse/"))
    print("🎁 Reuse/Donate page open"); pause()


    try:
        cat = WebDriverWait(driver, WAIT).until(EC.presence_of_element_located((By.NAME, "category")))
        highlight(cat); type_slow(cat, "Furniture"); pause(0.2)
    except TimeoutException:
        print("⚠️ Field not found: category")


    try:
        qty = WebDriverWait(driver, WAIT).until(EC.presence_of_element_located((By.NAME, "quantity")))
        highlight(qty); type_slow(qty, "2"); pause(0.2)
    except TimeoutException:
        print("⚠️ Field not found: quantity")


    try:
        partner = WebDriverWait(driver, WAIT).until(EC.presence_of_element_located((By.NAME, "partner")))
        highlight(partner); type_slow(partner, "Local Charity"); pause(0.2)
    except TimeoutException:
        print("ℹ️ No partner field (skipped)")


    try:
        note = WebDriverWait(driver, WAIT).until(EC.presence_of_element_located((By.NAME, "note")))
        highlight(note); type_slow(note, "Pickup after 5pm; ground floor."); pause(0.2)
    except TimeoutException:
        print("ℹ️ No note field (skipped)")


    try:
        photo = WebDriverWait(driver, 3).until(EC.presence_of_element_located((By.NAME, "photo")))
        if ASSET_PHOTO.exists():
            highlight(photo); photo.send_keys(str(ASSET_PHOTO.resolve())); pause(0.2)
        else:
            print(f"ℹ️ Photo file not found (skipped): {ASSET_PHOTO}")
    except TimeoutException:
        print("ℹ️ No photo field (skipped)")


    if not click_any(
        [
            (By.XPATH, "//button[@type='submit' and contains(.,'Save Donation')]"),
            (By.XPATH, "//button[@type='submit']"),
            (By.CSS_SELECTOR, "button[type='submit'],input[type='submit']"),
        ],
        desc="Submit Donation",
        fallback_url=None,
    ):
        f = WebDriverWait(driver, WAIT).until(EC.presence_of_element_located((By.XPATH, "//form")))
        highlight(f); f.submit(); pause()
        print("🖱️ Submitted via form.submit()")
    else:
        print("🖱️ Submit clicked")


    if wait_toast_success(): print("✅ Success toast found")
    else: print("ℹ️ No explicit success toast detected (proceeding)")
    pause(0.4, "📸 Taking screenshot of successful donation submit")
    ss("reuse_submit_success")


    click_any(
        [
            (By.XPATH, "//a[contains(@href,'/users/dashboard/')]"),
        ],
        desc="Dashboard",
        fallback_url=DASHBOARD_URL,
    )
    WebDriverWait(driver, WAIT).until(lambda d: is_dash(d.current_url))
    print("➡️ Back on Dashboard"); pause()


    logged_out = click_any(
        [
            (By.XPATH, "//header//a[contains(@href,'/users/logout/')]"),
            (By.XPATH, "//aside//a[contains(@href,'/users/logout/')]"),
        ],
        desc="Logout",
        fallback_url=None,
    )
    if not logged_out:
        try:
            lf = WebDriverWait(driver, 3).until(
                EC.presence_of_element_located((By.XPATH, "//form[contains(@action,'/users/logout')]"))
            )
            highlight(lf); lf.submit(); pause()
            logged_out = True
        except TimeoutException:
            logged_out = False
    if not logged_out:
        driver.get(LOGOUT_URL); pause()

    if not wait_logged_out():
        print("ℹ️ Could not confirm logged-out state; forcing login page")
        driver.get(LOGIN_URL)
    pause(0.4, "📸 Taking screenshot after logout")
    ss("after_logout")

    print("✅ Flow complete: login → reuse submit → dashboard → logout")

finally:
    pause(0.3)
    driver.quit()
    print("🚪 Browser closed.")
