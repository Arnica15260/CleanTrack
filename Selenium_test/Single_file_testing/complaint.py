# Selenium_test/complaint_flow_simple.py
import time
from pathlib import Path
from datetime import datetime
from urllib.parse import urlparse

from selenium import webdriver
from selenium.common.exceptions import (
    TimeoutException,
    StaleElementReferenceException,
    ElementClickInterceptedException,
)
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC


BASE            = "http://127.0.0.1:8000/"
LOGIN_URL       = f"{BASE}/users/login/"
DASHBOARD_URL   = f"{BASE}/users/dashboard/"
COMPLAINT_URL   = f"{BASE}/users/complaint/"
LOGOUT_URL      = f"{BASE}/users/logout/"


USERNAME = "Rahman"
PASSWORD = "V=u+at15260"

WAIT            = 20
STEP_PAUSE      = 0.9
TYPE_DELAY      = 0.035
HILITE_MS       = 250
RETRY_STALE_MAX = 2

SS_DIR = Path("../Selenium_test/screens"); SS_DIR.mkdir(parents=True, exist_ok=True)


def pause(*args, **kwargs):
    sec = kwargs.get("sec", STEP_PAUSE)
    msg = kwargs.get("msg")
    if args:
        if isinstance(args[0], (int, float)):
            sec = args[0]
            if len(args) > 1 and isinstance(args[1], str): msg = args[1]
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

def dismiss_toasts(timeout=4):

    try:
        stack = WebDriverWait(driver, 1.0).until(
            EC.presence_of_element_located((By.ID, "toast-stack"))
        )
    except TimeoutException:
        return
    for btn in stack.find_elements(By.CSS_SELECTOR, ".toast .close"):
        try: driver.execute_script("arguments[0].click();", btn)
        except Exception: pass
    t0 = time.time()
    while time.time() - t0 < timeout:
        if not driver.find_elements(By.CSS_SELECTOR, "#toast-stack .toast"): return
        time.sleep(0.15)
    try: driver.execute_script("const s=document.getElementById('toast-stack'); if(s) s.style.display='none';")
    except Exception: pass

def click_one(by, locator, desc=""):
    for attempt in range(1, RETRY_STALE_MAX + 2):
        try:
            el = WebDriverWait(driver, WAIT).until(EC.element_to_be_clickable((by, locator)))
            highlight(el)
            try:
                el.click()
            except ElementClickInterceptedException:
                dismiss_toasts(); pause(0.2)
                try:
                    driver.execute_script("arguments[0].click();", el)
                except Exception:
                    ActionChains(driver).move_to_element(el).pause(0.1).click().perform()
            if desc: print("🖱️ Clicked:", desc)
            pause()
            return True
        except StaleElementReferenceException:
            print(f"↻ Stale on {desc or locator} — retry {attempt}")
        except TimeoutException:
            return False
        except ElementClickInterceptedException:
            driver.execute_script("window.scrollTo(0,0);")
            try:
                el = driver.find_element(by, locator)
                driver.execute_script("arguments[0].click();", el)
                if desc: print("🖱️ Clicked (JS):", desc)
                pause()
                return True
            except Exception:
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
            WebDriverWait(driver, 6).until(EC.presence_of_element_located((by, sel)))
            return True
        except TimeoutException:
            continue
    return False

def find_asset_image(candidates=("complaint_sample.png","complaint_sample.jpg",
                                 "schedule_sample.jpg","recycling_sample.jpg","reuse_sample.png")):
    bases = [Path(__file__).resolve().parent, Path(__file__).resolve().parent.parent, Path.cwd()]
    subs  = ["assets", "Selenium_test/assets", "Selenium_test/Selenium_test/assets"]
    for base in bases:
        for sub in subs:
            for name in candidates:
                p = (base / sub / name).resolve()
                if p.exists():
                    print(f"🖼️ Using photo: {p}")
                    return p
    return None

ASSET_PHOTO = find_asset_image()


driver = webdriver.Chrome()
driver.set_window_size(1280, 900)

try:
    # LOGIN
    driver.get(LOGIN_URL); pause("➡️ Login page loaded")
    u = WebDriverWait(driver, WAIT).until(EC.visibility_of_element_located((By.NAME, "username")))
    print("⌨️ Typing username…"); type_slow(u, USERNAME)
    p = WebDriverWait(driver, WAIT).until(EC.visibility_of_element_located((By.NAME, "password")))
    print("⌨️ Typing password…"); type_slow(p, PASSWORD)
    form = u.find_element(By.XPATH, "ancestor::form"); highlight(form); form.submit(); print("🖱️ Submitted login form")

    try:
        WebDriverWait(driver, WAIT).until(lambda d: is_dash(d.current_url))
    except TimeoutException:
        driver.get(DASHBOARD_URL)
        WebDriverWait(driver, WAIT).until(lambda d: is_dash(d.current_url))
    print("➡️ Landed on Dashboard"); pause()


    click_any(
        [
            (By.XPATH, "//aside//a[contains(@href,'/users/complaint/')]"),
            (By.XPATH, "//a[contains(@href,'/users/complaint/')]"),
        ],
        desc="Complaint",
        fallback_url=COMPLAINT_URL,
    )
    WebDriverWait(driver, WAIT).until(EC.url_contains("/users/complaint/"))
    print("📝 Complaint page open"); pause()


    try:
        ctype = WebDriverWait(driver, WAIT).until(EC.presence_of_element_located((By.NAME, "complaint_type")))
        highlight(ctype)
        if ctype.tag_name.lower() == "select":
            try:
                Select(ctype).select_by_visible_text("Service Issue")
            except Exception:
                # pick first non-empty option
                opts = ctype.find_elements(By.TAG_NAME, "option")
                for o in opts:
                    if o.get_attribute("value"):
                        o.click(); break
        else:
            type_slow(ctype, "Service Issue")
        pause(0.2)
    except TimeoutException:
        print("⚠️ Field not found (complaint_type)")


    try:
        subj = WebDriverWait(driver, WAIT).until(EC.presence_of_element_located((By.NAME, "subject")))
        highlight(subj); type_slow(subj, "Missed pickup on my street"); pause(0.2)
    except TimeoutException:
        print("⚠️ Field not found (subject)")


    try:
        desc = WebDriverWait(driver, WAIT).until(EC.presence_of_element_located((By.NAME, "description")))
        highlight(desc); type_slow(desc, "Scheduled pickup missed yesterday (10:30–12:00 window). Please advise next collection."); pause(0.2)
    except TimeoutException:
        print("⚠️ Field not found (description)")


    try:
        photo = WebDriverWait(driver, 3).until(EC.presence_of_element_located((By.NAME, "photo")))
        if ASSET_PHOTO:
            highlight(photo); photo.send_keys(str(ASSET_PHOTO)); pause(0.2)
        else:
            print("ℹ️ Photo file not found (skipped upload)")
    except TimeoutException:
        print("ℹ️ No photo field (skipped)")


    if not click_any(
        [
            (By.XPATH, "//button[@type='submit' and contains(.,'Submit Complaint')]"),
            (By.XPATH, "//button[@type='submit']"),
            (By.CSS_SELECTOR, "button[type='submit'],input[type='submit']"),
        ],
        desc="Submit Complaint",
        fallback_url=None,
    ):

        f = WebDriverWait(driver, WAIT).until(EC.presence_of_element_located((By.XPATH, "//form")))
        highlight(f); f.submit(); pause()
        print("🖱️ Submitted via form.submit()")
    else:
        print("🖱️ Submit clicked")




    click_any([(By.XPATH, "//a[contains(@href,'/users/dashboard/')]")], "Dashboard", fallback_url=DASHBOARD_URL)
    try:
        WebDriverWait(driver, 8).until(lambda d: is_dash(d.current_url))
    except TimeoutException:
        print("ℹ️ Could not confirm dashboard URL, continuing anyway")
    print("➡️ Back on Dashboard"); pause()


    dismiss_toasts()
    if not click_any(
        [
            (By.XPATH, "//header//a[contains(@href,'/users/logout/')]"),
            (By.XPATH, "//aside//a[contains(@href,'/users/logout/')]"),
        ],
        desc="Logout",
        fallback_url=None,
    ):
        try:
            lf = WebDriverWait(driver, 3).until(
                EC.presence_of_element_located((By.XPATH, "//form[contains(@action,'/users/logout')]"))
            )
            highlight(lf); lf.submit(); pause()
        except TimeoutException:
            driver.get(LOGOUT_URL); pause()

    try:
        WebDriverWait(driver, 6).until(EC.url_contains("/users/login/"))
    except TimeoutException:
        pass
    pause(0.3, "📸 Taking screenshot after logout")
    ss("complaint_after_logout")

    print("✅ Flow complete: login → complaint submit → dashboard → logout")

finally:
    pause(0.3)
    driver.quit()
    print("🚪 Browser closed.")
