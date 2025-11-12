# Selenium_test/login_forgot_password_flow_with_header_nav.py
import time
from pathlib import Path
from datetime import datetime
from urllib.parse import urlparse

from selenium import webdriver
from selenium.common.exceptions import (
    TimeoutException, ElementClickInterceptedException,
    StaleElementReferenceException, NoSuchElementException
)
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


BASE                 = "http://127.0.0.1:8000"
HOME_URL             = f"{BASE}/"
LOGIN_URL            = f"{BASE}/users/login/"
RESET_URL            = f"{BASE}/users/password-reset/"
RESET_DONE_URL       = f"{BASE}/users/password-reset/done/"
CONTACT_URL          = f"{BASE}/users/contact/"


WAIT       = 6
TYPE_DELAY = 0.012

SS_DIR = Path("../Selenium_test/screens")
SS_DIR.mkdir(parents=True, exist_ok=True)

def ss(name: str):
    p = SS_DIR / f"{name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
    driver.save_screenshot(str(p)); print("📸", p)

def norm_path(url: str) -> str:
    p = urlparse(url); path = p.path or "/"
    return path[:-1] if len(path) > 1 and path.endswith("/") else path

def is_home(url: str) -> bool:
    return norm_path(url) == "/"

def is_login(url: str) -> bool:
    return norm_path(url).startswith("/users/login")

def is_reset(url: str) -> bool:
    return norm_path(url).startswith("/users/password-reset")

def is_reset_done(url: str) -> bool:
    return norm_path(url).startswith("/users/password-reset/done")

def wait_url(check_fn, timeout=WAIT):
    WebDriverWait(driver, timeout).until(lambda d: check_fn(d.current_url))

def click_js(el): driver.execute_script("arguments[0].click();", el)

def click_safely(el, label=""):
    try:
        el.click()
        print(f"🖱️ Click: {label or el.get_attribute('innerText') or '<element>'}")
        return True
    except ElementClickInterceptedException:
        try:
            click_js(el)
            print(f"🖱️ Click (JS): {label or '<element>'}")
            return True
        except Exception:
            try:
                ActionChains(driver).move_to_element(el).pause(0.02).click().perform()
                print(f"🖱️ Click (Actions): {label or '<element>'}")
                return True
            except Exception:
                print(f"⛔ Click failed: {label or '<element>'}")
                return False
    except Exception:
        try:
            click_js(el)
            print(f"🖱️ Click (JS): {label or '<element>'}")
            return True
        except Exception:
            print(f"⛔ Click failed: {label or '<element>'}")
            return False

def type_slow(el, text):
    try: el.clear()
    except Exception: pass
    for ch in str(text):
        el.send_keys(ch)
        time.sleep(TYPE_DELAY)

def find_clickable(locators, label=""):
    for by, sel in locators:
        try:
            return WebDriverWait(driver, 2).until(EC.element_to_be_clickable((by, sel)))
        except TimeoutException:
            continue
    raise NoSuchElementException(f"Element not found for {label}")

def go_home_fast():
    # Use your header logo or Home button
    tries = [
        (By.CSS_SELECTOR, "header.topbar a.nav-btn[href='/']"),
        (By.LINK_TEXT, "Home"),
        (By.PARTIAL_LINK_TEXT, "Home"),
        (By.CSS_SELECTOR, "header.topbar .logo-pill"),  # clickable? if not, next fallbacks
        (By.XPATH, "//header//a[@href='/' or @href='/home/']"),
    ]
    for by, sel in tries:
        try:
            el = WebDriverWait(driver, 1.5).until(EC.element_to_be_clickable((by, sel)))
            click_safely(el, "Header: Home"); break
        except TimeoutException:
            continue
    else:
        print("↪️ Direct nav: Home"); driver.get(HOME_URL)
    try: wait_url(is_home, timeout=WAIT)
    except TimeoutException: pass
    print(f"🏠 On Home: {driver.current_url}")

def header_nav_from_reset():

    print("\n===== HEADER NAV FROM RESET PAGE =====")


    go_home_fast(); ss("nav_back_home_from_about")


    try:
        contact = find_clickable([
            (By.XPATH, "//header//a[contains(@href,'/users/contact/')]"),
            (By.LINK_TEXT, "Contact"), (By.PARTIAL_LINK_TEXT, "Contact"),
        ], "Header: Contact")
        click_safely(contact, "Header: Contact")
        try: WebDriverWait(driver, WAIT).until(EC.url_contains("/users/contact/"))
        except TimeoutException: pass
        print(f"➡️ On Contact: {driver.current_url}"); ss("nav_contact_from_reset")
    except NoSuchElementException:
        print("ℹ️ Contact link not found on header (skipping)")


    go_home_fast(); ss("nav_back_home_from_contact")


    try:
        login = find_clickable([
            (By.XPATH, "//header//a[contains(@href,'/users/login/')]"),
            (By.LINK_TEXT, "Login"), (By.PARTIAL_LINK_TEXT, "Login"),
        ], "Header: Login")
        click_safely(login, "Header: Login")
        try: WebDriverWait(driver, WAIT).until(EC.url_contains("/users/login/"))
        except TimeoutException: pass
        print(f"➡️ On Login: {driver.current_url}"); ss("nav_login_from_reset")
    except NoSuchElementException:
        print("ℹ️ Login link not found on header (skipping)")


    go_home_fast(); ss("nav_back_home_from_login")


opts = webdriver.ChromeOptions()
opts.page_load_strategy = "eager"
opts.add_argument("--disable-renderer-backgrounding")
opts.add_argument("--disable-features=PaintHolding")


driver = webdriver.Chrome(options=opts)
driver.set_window_size(1360, 900)

try:

    driver.get(LOGIN_URL)
    try: wait_url(is_login, timeout=WAIT)
    except TimeoutException: pass
    print(f"📍 On Login: {driver.current_url}")
    ss("login_loaded")


    print("→ Click: Forgot password?")
    forgot_el = find_clickable([
        (By.XPATH, "//a[contains(@href,'/users/password-reset/')]"),
        (By.XPATH, "//a[contains(translate(normalize-space(.),'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'forgot')]"),
        (By.LINK_TEXT, "Forgot password?"),
        (By.PARTIAL_LINK_TEXT, "Forgot"),
    ], "Forgot password link")
    click_safely(forgot_el, "Forgot password?")
    try: wait_url(is_reset, timeout=WAIT)
    except TimeoutException: pass
    print(f"✔ Reset form: {driver.current_url}")
    ss("reset_form_loaded")


    print("→ Fill: email and submit")
    email = WebDriverWait(driver, WAIT).until(EC.presence_of_element_located((By.NAME, "email")))
    type_slow(email, f"qa+{int(time.time())}@example.com")

    submit_btn = find_clickable([
        (By.CSS_SELECTOR, "form button[type='submit']"),
        (By.XPATH, "//form//button[@type='submit' or contains(.,'Reset') or contains(.,'Send')]"),
        (By.XPATH, "//input[@type='submit']"),
    ], "Reset submit")
    click_safely(submit_btn, "Send reset link")
    try: wait_url(is_reset_done, timeout=WAIT)
    except TimeoutException: pass
    print(f"✔ Reset done: {driver.current_url}")
    ss("reset_submitted_done")


    header_nav_from_reset()

    print("✅ Forgot password + header nav flow complete.")
finally:
    driver.quit()
    print("🚪 Browser closed.")
