
import time
from pathlib import Path
from datetime import datetime


from selenium import webdriver
from selenium.common.exceptions import StaleElementReferenceException, TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

BASE          = "http://127.0.0.1:8000"
LOGIN_URL     = f"{BASE}/users/login/"
DASHBOARD_URL = f"{BASE}/users/dashboard/"
PROFILE_URL   = f"{BASE}/users/profile/"
LOGOUT_URL    = f"{BASE}/users/logout/"

USERNAME = "Rahman"
PASSWORD = "V=u+at15260"

WAIT            = 20
STEP_PAUSE      = 0.8
TYPE_DELAY      = 0.04
HILITE_MS       = 300
RETRY_STALE_MAX = 2

SS_DIR = Path("../Selenium_test/screens"); SS_DIR.mkdir(parents=True, exist_ok=True)

def pause(sec=STEP_PAUSE, msg=None):
    if msg: print(msg)
    time.sleep(sec)

def ss(name):
    p = SS_DIR / f"{name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
    driver.save_screenshot(str(p)); print("📸", p)

def norm_path(url: str) -> str:
    from urllib.parse import urlparse
    p = urlparse(url); path = p.path or "/"
    return path[:-1] if len(path) > 1 and path.endswith("/") else path

def is_dash(url: str) -> bool:
    return norm_path(url).startswith("/users/dashboard")

def type_slow(el, text):
    el.clear()
    for ch in text:
        el.send_keys(ch); time.sleep(TYPE_DELAY)

def highlight(el):
    driver.execute_script("arguments[0].scrollIntoView({block:'center'});", el)
    original = el.get_attribute("style") or ""
    driver.execute_script(
        "arguments[0].setAttribute('style', arguments[1]);",
        el, f"{original}; outline: 3px solid #24a0ed; outline-offset: 2px;"
    )
    time.sleep(HILITE_MS/1000)
    driver.execute_script("arguments[0].setAttribute('style', arguments[1]);", el, original)

def find_click(by, locator, desc="", fallback_url=None):
    """Locate fresh each time; retry if stale; fallback to URL if provided."""
    for attempt in range(1, RETRY_STALE_MAX + 2):
        try:
            el = WebDriverWait(driver, WAIT).until(EC.element_to_be_clickable((by, locator)))
            highlight(el); el.click()
            if desc: print("🖱️ Clicked:", desc)
            pause()
            return True
        except StaleElementReferenceException:
            print(f"↻ Stale on {desc or locator} (attempt {attempt}) — re-finding…")
            if attempt >= RETRY_STALE_MAX + 1:
                break
        except TimeoutException:
            break
    if fallback_url:
        print(f"⚠️ Couldn’t click {desc or locator}. Navigating to:", fallback_url)
        driver.get(fallback_url); pause()
        return True
    return False

def wait_for_login_page():
    """Some apps log out but stay on same URL; accept either the URL OR the login form."""
    try:
        WebDriverWait(driver, 6).until(EC.url_contains("/users/login/"))
        return True
    except TimeoutException:
        pass
    try:
        WebDriverWait(driver, WAIT).until(EC.visibility_of_element_located((By.NAME, "username")))
        return True
    except TimeoutException:
        return False

driver = webdriver.Chrome()
driver.set_window_size(1280, 900)

try:

    driver.get(LOGIN_URL); pause(msg="➡️ Login page loaded")

    user_el = WebDriverWait(driver, WAIT).until(EC.visibility_of_element_located((By.NAME, "username")))
    print("⌨️ Typing username…"); type_slow(user_el, USERNAME); pause(0.3)

    pass_el = WebDriverWait(driver, WAIT).until(EC.visibility_of_element_located((By.NAME, "password")))
    print("⌨️ Typing password…"); type_slow(pass_el, PASSWORD); pause(0.3)


    form = user_el.find_element(By.XPATH, "ancestor::form")
    highlight(form)
    form.submit()
    print("🖱️ Submitted login form")

    try:
        WebDriverWait(driver, WAIT).until(lambda d: is_dash(d.current_url))
    except TimeoutException:
        driver.get(DASHBOARD_URL); WebDriverWait(driver, WAIT).until(lambda d: is_dash(d.current_url))
    print("➡️ Landed on Dashboard"); pause()


    find_click(By.XPATH, "//a[contains(@href,'/users/profile/')]", "Profile", fallback_url=PROFILE_URL)
    WebDriverWait(driver, WAIT).until(EC.url_contains("/users/profile/"))
    pause(0.5, "👤 Profile open — taking screenshot")
    ss("profile_open")


    find_click(
        By.XPATH,
        "//a[contains(@href,'/users/dashboard/')] | //nav//*[contains(text(),'Dashboard')]/ancestor::a",
        "Dashboard",
        fallback_url=DASHBOARD_URL
    )
    WebDriverWait(driver, WAIT).until(lambda d: is_dash(d.current_url))
    print("➡️ Back on Dashboard"); pause()


    if not find_click(
        By.XPATH,
        "//a[contains(@href,'/users/logout/')] | //button[contains(@onclick,'logout')] | //form[contains(@action,'/users/logout')]/button",
        "Logout",
        fallback_url=LOGOUT_URL
    ):

        try:
            logout_form = WebDriverWait(driver, 4).until(
                EC.presence_of_element_located((By.XPATH, "//form[contains(@action,'/users/logout')]"))
            )
            highlight(logout_form); logout_form.submit(); pause()
        except TimeoutException:
            pass

    if not wait_for_login_page():

        driver.get(LOGIN_URL)
        WebDriverWait(driver, WAIT).until(EC.visibility_of_element_located((By.NAME, "username")))

    pause(0.5, "🚪 Logged out — taking screenshot")
    ss("after_logout")

    print("✅ Slow demo complete: login → profile → dashboard → logout")

finally:
    pause(0.4)
    driver.quit()
    print("🚪 Browser closed.")
