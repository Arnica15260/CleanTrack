
import time
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException, NoSuchElementException, ElementClickInterceptedException
)


BASE              = " http://127.0.0.1:8000"
HOME_URL          = f"{BASE}/"
LOGIN_URL         = f"{BASE}/users/login/"
DASHBOARD_URL     = f"{BASE}/users/dashboard/"
LOGOUT_URL        = f"{BASE}/users/logout/"
ADMIN_INDEX_URL   = f"{BASE}/admin/"


DRIVER_USERNAME = "Rahim"
DRIVER_PASSWORD = "V=u+at15260"

ADMIN_USERNAME  = "Arnica"
ADMIN_PASSWORD  = "12345"


WAIT = 8
TYPE_DELAY = 0.012

SS_DIR = Path("../Selenium_test/screens")
SS_DIR.mkdir(parents=True, exist_ok=True)

def ss(driver, name):
    p = SS_DIR / f"{name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
    driver.save_screenshot(str(p))
    print("📸", p)

def norm_path(url: str) -> str:
    p = urlparse(url)
    path = p.path or "/"
    return path[:-1] if len(path) > 1 and path.endswith("/") else path

def is_home(url: str) -> bool:
    return norm_path(url) == "/"

def is_user_dash(url: str) -> bool:
    return norm_path(url).startswith("/users/dashboard")

def is_admin_index(url: str) -> bool:
    return norm_path(url).startswith("/admin")

def type_slow(el, text):
    try: el.clear()
    except Exception: pass
    for ch in str(text):
        el.send_keys(ch)
        time.sleep(TYPE_DELAY)

def click_js(driver, el, label=""):
    try:
        el.click()
    except ElementClickInterceptedException:
        driver.execute_script("arguments[0].click();", el)
    print(f"🖱️ Click: {label or el.get_attribute('innerText') or '<element>'}")

def find_first(driver, locators):
    for by, sel in locators:
        els = driver.find_elements(by, sel)
        if els:
            return els[0]
    return None


def header_click_home(driver):

    for attempt in range(3):
        el = find_first(driver, [
            (By.XPATH, "//header//a[normalize-space()='Home']"),
            (By.XPATH, "//header//*[self::a or self::button][normalize-space()='Home']"),
            (By.XPATH, "//header//a[@href='/' or @href='/home/' or contains(@href,'/')]"),
        ])
        if el:
            try:
                driver.execute_script("arguments[0].scrollIntoView({block:'center'});", el)
                driver.execute_script("arguments[0].click();", el)
                print("🖱️ Click: Header: Home")
            except Exception:
                pass

            t0 = time.time()
            while time.time() - t0 < 1.5:
                if is_home(driver.current_url):
                    return
                time.sleep(0.1)
        time.sleep(0.2)

    print("↪️ Forcing direct nav to HOME")
    driver.get(HOME_URL)

def header_click_login(driver):
    for attempt in range(2):
        el = find_first(driver, [
            (By.XPATH, "//ul[contains(@class,'nav-links')]//a[contains(@href,'/users/login/')]"),
            (By.XPATH, "//header//a[normalize-space()='Login']"),
            (By.XPATH, "//header//a[contains(@href,'/users/login/')]"),
        ])
        if el:
            try:
                driver.execute_script("arguments[0].scrollIntoView({block:'center'});", el)
                driver.execute_script("arguments[0].click();", el)
                print("🖱️ Click: Header: Login")
            except Exception:
                pass

            time.sleep(0.3)
            return
        time.sleep(0.2)
    print("↪️ Direct nav to /users/login/")
    driver.get(LOGIN_URL)

def header_click_admin(driver):
    for attempt in range(2):
        el = find_first(driver, [
            (By.XPATH, "//ul[contains(@class,'nav-links')]//a[normalize-space()='Admin']"),
            (By.XPATH, "//header//a[normalize-space()='Admin']"),
            (By.XPATH, "//header//a[contains(@href,'/admin/')]"),
        ])
        if el:
            try:
                driver.execute_script("arguments[0].scrollIntoView({block:'center'});", el)
                driver.execute_script("arguments[0].click();", el)
                print("🖱️ Click: Header: Admin")
            except Exception:
                pass
            time.sleep(0.4)
            return
        time.sleep(0.2)
    print("↪️ No Admin link — going directly to /admin/")
    driver.get(ADMIN_INDEX_URL)

def do_normal_login(driver, username, password, label=""):
    driver.get(LOGIN_URL)
    ss(driver, f"{label}_login_loaded" if label else "login_loaded")

    # fresh lookups, no waits that call is_displayed()
    user_input = find_first(driver, [
        (By.NAME, "username"),
        (By.NAME, "login"),
        (By.CSS_SELECTOR, "input[name='username'],input[name='login']"),
    ])
    if not user_input:
        raise RuntimeError("Username field not found")
    type_slow(user_input, username)

    pwd_input = find_first(driver, [(By.NAME, "password")])
    if not pwd_input:
        raise RuntimeError("Password field not found")
    type_slow(pwd_input, password)

    submit = find_first(driver, [
        (By.CSS_SELECTOR, "button[type='submit']"),
        (By.CSS_SELECTOR, "input[type='submit']"),
        (By.XPATH, "//button[contains(.,'Log in') or contains(.,'Login')]"),
    ])
    if not submit:
        raise RuntimeError("Login submit button not found")
    ss(driver, f"{label}_before_submit" if label else "before_submit")
    click_js(driver, submit, f"{label} login submit".strip())

def do_app_logout(driver):
    print("→ App Logout")
    el = find_first(driver, [
        (By.XPATH, "//a[contains(@href,'/users/logout/')]"),
        (By.LINK_TEXT, "Logout"),
        (By.PARTIAL_LINK_TEXT, "Logout"),
    ])
    if el:
        click_js(driver, el, "Logout")
        time.sleep(0.2)
    else:
        driver.get(LOGOUT_URL)
        time.sleep(0.2)

def go_home(driver):
    driver.get(HOME_URL)
    # not strict; just a tiny wait
    t0 = time.time()
    while time.time() - t0 < 1.5:
        if is_home(driver.current_url): break
        time.sleep(0.1)
    print("🏠 On Home")
    ss(driver, "home")

# ---------- Flow ----------
def login_driver_logout_home(driver):
    print("\n==== DRIVER via NORMAL LOGIN → LOGOUT → HOME ====")
    do_normal_login(driver, DRIVER_USERNAME, DRIVER_PASSWORD, label="driver")
    try:
        WebDriverWait(driver, WAIT).until(lambda d: is_user_dash(d.current_url))
        print("✅ Landed on USER DASHBOARD")
    except TimeoutException:
        print("ℹ️ Could not confirm dashboard; current:", driver.current_url)
    ss(driver, "driver_after_submit")

    do_app_logout(driver)
    go_home(driver)

def admin_via_normal_login_then_admin_index_then_logout_home(driver):
    print("\n==== ADMIN via NORMAL LOGIN → ADMIN INDEX → LOGOUT → HOME ====")
    print("→ Header nav to Login (from Home)")
    header_click_login(driver)
    ss(driver, "from_home_after_click_login")

    do_normal_login(driver, ADMIN_USERNAME, ADMIN_PASSWORD, label="admin_normal")


    header_click_home(driver)


    header_click_admin(driver)
    if is_admin_index(driver.current_url):
        print("✅ On Django Admin index")
    else:
        print("ℹ️ Admin index not confirmed; current:", driver.current_url)
    ss(driver, "admin_index_open")

    do_app_logout(driver)
    go_home(driver)


if __name__ == "__main__":
    opts = webdriver.ChromeOptions()
    opts.page_load_strategy = "eager"
    # opts.add_argument("--headless=new")
    driver = webdriver.Chrome(options=opts)
    driver.set_window_size(1280, 900)

    try:
        login_driver_logout_home(driver)
        admin_via_normal_login_then_admin_index_then_logout_home(driver)
        print("\n✅ Flow complete: driver(normal) → logout → Home → header Login → admin(normal) → Admin index → logout → Home")
    finally:
        time.sleep(0.3)
        driver.quit()
        print("🚪 Browser closed.")
