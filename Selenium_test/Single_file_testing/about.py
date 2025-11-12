# Selenium_test/about_page_flow.py
import time
from pathlib import Path
from datetime import datetime
from urllib.parse import urlparse

from selenium import webdriver
from selenium.common.exceptions import TimeoutException, ElementClickInterceptedException, StaleElementReferenceException
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


BASE         = " http://127.0.0.1:8000"
HOME_URL     = f"{BASE}/"
ABOUT_URL    = f"{BASE}/users/about/"
CONTACT_URL  = f"{BASE}/users/contact/"
SIGNUP_URL   = f"{BASE}/users/signup/"
LOGIN_URL    = f"{BASE}/users/login/"


WAIT       = 6
TYPE_DELAY = 0.004
RETRY_STALE_MAX = 2


SS_DIR = Path("../Selenium_test/screens")
SS_DIR.mkdir(parents=True, exist_ok=True)

def ss(name: str):
    p = SS_DIR / f"{name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
    driver.save_screenshot(str(p))
    print("📸", p)


def norm_path(url: str) -> str:
    p = urlparse(url); path = p.path or "/"
    return path[:-1] if len(path) > 1 and path.endswith("/") else path

def is_home(url: str) -> bool:
    return norm_path(url) == "/"

def is_about(url: str) -> bool:
    return norm_path(url).startswith("/users/about")

def is_contact(url: str) -> bool:
    return norm_path(url).startswith("/users/contact")

def is_signup(url: str) -> bool:
    return norm_path(url).startswith("/users/signup")

def is_login(url: str) -> bool:
    return norm_path(url).startswith("/users/login")

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

def header_click_and_log(text_or_href, visible_text, expect_fn, to_url=None):
    """Find header link by href/text, click, log, and confirm (fast)."""
    print(f"→ Trying header: {visible_text}")
    locators = [
        (By.XPATH, f"//ul[contains(@class,'nav-links')]//a[contains(@href,'{text_or_href}')]"),
        (By.LINK_TEXT, visible_text),
        (By.PARTIAL_LINK_TEXT, visible_text),
    ]
    clicked = False
    for by, sel in locators:
        try:
            el = WebDriverWait(driver, 2).until(EC.element_to_be_clickable((by, sel)))
            clicked = click_safely(el, visible_text)
            if clicked: break
        except (TimeoutException, StaleElementReferenceException):
            continue
    if not clicked:

        print(f"↪️ Direct nav: {visible_text} -> {to_url or text_or_href}")
        driver.get(to_url or text_or_href)

    try: wait_url(expect_fn, timeout=WAIT)
    except TimeoutException: pass
    print(f"✔ Reached: {driver.current_url}")

def go_home_via_logo_fast():
    tries = [
        (By.CSS_SELECTOR, "header.header a.logo"),
        (By.XPATH, "//a[contains(@class,'logo') and contains(.,'CleanTrack+')]"),
        (By.XPATH, "//header//a[@href='/' or @href='/home/' or contains(@href,'/')]"),
    ]
    for by, sel in tries:
        try:
            el = WebDriverWait(driver, 1.5).until(EC.element_to_be_clickable((by, sel)))
            click_safely(el, "Logo → Home"); break
        except TimeoutException:
            continue
    else:
        print("↪️ Direct nav: Home")
        driver.get(HOME_URL)
    try: wait_url(is_home, timeout=WAIT)
    except TimeoutException: pass
    print(f"🏠 Back Home: {driver.current_url}")

def go_about_fast():
    print("↪️ Back to About")
    driver.get(ABOUT_URL)
    try: wait_url(is_about, timeout=WAIT)
    except TimeoutException: pass
    print(f"📍 On About: {driver.current_url}")

def full_page_scroll(pause_step=0.12, step_ratio=0.9):

    try:
        last_height = driver.execute_script("return document.body.scrollHeight || document.documentElement.scrollHeight;")
        y = 0
        inner_h = driver.execute_script("return window.innerHeight;") or 800
        step = int(inner_h * step_ratio)
        print("↧ Scrolling About page...")
        while True:
            y += step
            driver.execute_script("window.scrollTo(0, arguments[0]);", y)
            time.sleep(pause_step)
            new_height = driver.execute_script("return document.body.scrollHeight || document.documentElement.scrollHeight;")
            # extend if page grows (lazy content)
            last_height = max(last_height, new_height)
            if y + inner_h >= last_height - 2:
                break

        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(0.15)
        print("⤓ Reached bottom.")
    except Exception as e:
        print("ℹ️ Scroll error (ignored):", e)

def header_cycle_from_about():

    print("\n===== HEADER NAV (from About) =====")
    go_about_fast()

    # Home (via logo) -> About
    go_home_via_logo_fast()
    go_about_fast()

    # Signup -> Home -> About
    header_click_and_log("/users/signup/", "Signup", is_signup, SIGNUP_URL)
    go_home_via_logo_fast()
    go_about_fast()

    # Login -> Home -> About
    header_click_and_log("/users/login/", "Login", is_login, LOGIN_URL)
    go_home_via_logo_fast()
    go_about_fast()

    # Contact -> Home (finish on Home)
    header_click_and_log("/users/contact/", "Contact", is_contact, CONTACT_URL)
    go_home_via_logo_fast()

    print("✅ Header navigation cycle complete")


opts = webdriver.ChromeOptions()
opts.page_load_strategy = "eager"
opts.add_argument("--disable-renderer-backgrounding")
opts.add_argument("--disable-features=PaintHolding")


driver = webdriver.Chrome(options=opts)
driver.set_window_size(1360, 900)

try:

    driver.get(ABOUT_URL)
    try: wait_url(is_about, timeout=WAIT)
    except TimeoutException: pass
    print(f"📍 On About: {driver.current_url}")
    ss("about_loaded")

    full_page_scroll(pause_step=0.10, step_ratio=0.92)
    ss("about_scrolled_bottom")


    header_cycle_from_about()

    print("\n✅ About page flow complete.")
finally:
    driver.quit()
    print("🚪 Browser closed.")
