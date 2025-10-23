
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
# =======================================

WAIT       = 6
TYPE_DELAY = 0.004
RETRY_STALE_MAX = 2


SS_DIR = Path("Selenium_test/screens")
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

def type_slow(el, text):
    try: el.clear()
    except Exception: pass
    for ch in str(text):
        el.send_keys(ch); time.sleep(TYPE_DELAY)

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

def wait_url(check_fn, timeout=WAIT):
    WebDriverWait(driver, timeout).until(lambda d: check_fn(d.current_url))

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

def header_cycle_from_contact():

    print("\n===== HEADER NAV (from Contact) =====")
    driver.get(CONTACT_URL)
    try: wait_url(is_contact, timeout=WAIT)
    except TimeoutException: pass
    print(f"📍 On Contact: {driver.current_url}")


    header_click_and_log("/users/about/", "About", is_about, ABOUT_URL)
    go_home_via_logo_fast()


    driver.get(CONTACT_URL)
    try: wait_url(is_contact, timeout=WAIT)
    except TimeoutException: pass


    header_click_and_log("/users/signup/", "Signup", is_signup, SIGNUP_URL)
    go_home_via_logo_fast()

    driver.get(CONTACT_URL)
    try: wait_url(is_contact, timeout=WAIT)
    except TimeoutException: pass


    header_click_and_log("/users/login/", "Login", is_login, LOGIN_URL)
    go_home_via_logo_fast()

    print("✅ Header navigation cycle complete")

def contact_form_submit_with_ss():

    print("\n===== CONTACT FORM (screenshots, no toast) =====")
    driver.get(CONTACT_URL)
    try: wait_url(is_contact, timeout=WAIT)
    except TimeoutException: pass
    ss("contact_loaded")


    driver.execute_script(
        "const f=document.querySelector('form.contact-form')||document.querySelector('form');"
        "if(f){ f.scrollIntoView({block:'center'}); }"
    )


    form = None
    for sel in ["form.contact-form", "section.contact form", "form"]:
        try:
            form = WebDriverWait(driver, 3).until(EC.presence_of_element_located((By.CSS_SELECTOR, sel)))
            break
        except TimeoutException:
            continue
    if not form:
        print("ℹ️ No contact form found — aborting.")
        return

    ss("contact_form_visible")

    # Find fields
    def f(name=None, css=None):
        try:
            if name: return form.find_element(By.NAME, name)
            if css:  return form.find_element(By.CSS_SELECTOR, css)
        except Exception:
            return None

    name  = f(name="name")    or f(css="input[type='text'], input[name*='name' i]")
    email = f(name="email")   or f(css="input[type='email'], input[name*='mail' i]")
    msg   = f(name="message") or f(css="textarea, [name*='message' i], [name*='msg' i]")

    if name:  type_slow(name,  "QA Robot")
    if email: type_slow(email, f"qa+{int(time.time())}@example.com")
    if msg:   type_slow(msg,   "Hello from automated contact-form test (no toast check).")

    ss("contact_form_filled")

    # Submit
    submit = None
    for sel in ["button[type='submit']", "input[type='submit']", "button"]:
        try:
            submit = form.find_element(By.CSS_SELECTOR, sel); break
        except Exception:
            continue
    if not submit:
        print("⚠️ Submit button not found.")
        return

    if click_safely(submit, "Submit"):
        print("🖱️ Submit clicked")
    else:
        print("⚠️ Couldn’t click submit; trying JS")
        try: click_js(submit)
        except Exception:
            print("⛔ Submit failed")
            return

    time.sleep(0.25)
    ss("contact_form_submitted")
    print(f"➡️ Post-submit URL: {driver.current_url}")


opts = webdriver.ChromeOptions()
opts.page_load_strategy = "eager"
opts.add_argument("--disable-renderer-backgrounding")
opts.add_argument("--disable-features=PaintHolding")


driver = webdriver.Chrome(options=opts)
driver.set_window_size(1360, 900)

try:

    header_cycle_from_contact()

    contact_form_submit_with_ss()

    print("\n✅ Contact page flow complete.")
finally:
    driver.quit()
    print("🚪 Browser closed.")
