# Selenium_test/home_full_flow.py
import time
from urllib.parse import urlparse

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, ElementClickInterceptedException, StaleElementReferenceException


BASE        = "http://127.0.0.1:8000"
HOME_URL    = f"{BASE}/"
ABOUT_URL   = f"{BASE}/users/about/"
CONTACT_URL = f"{BASE}/users/contact/"
SIGNUP_URL  = f"{BASE}/users/signup/"
LOGIN_URL   = f"{BASE}/users/login/"


WAIT       = 6
TYPE_DELAY = 0.01


def norm_path(url: str) -> str:
    p = urlparse(url); path = p.path or "/"
    return path[:-1] if len(path) > 1 and path.endswith("/") else path

def is_home(url: str) -> bool:
    return norm_path(url) == "/"

def type_slow(el, text):
    try: el.clear()
    except Exception: pass
    for ch in str(text):
        el.send_keys(ch)
        time.sleep(TYPE_DELAY)

def js_click(driver, el, label=""):
    try:
        el.click()
    except ElementClickInterceptedException:
        driver.execute_script("arguments[0].click();", el)
    except Exception:
        try:
            driver.execute_script("arguments[0].click();", el)
        except Exception:
            ActionChains(driver).move_to_element(el).pause(0.05).click().perform()
    if label:
        print(f"🖱️ Click: {label}")

def find_first(driver, locators):
    for by, sel in locators:
        els = driver.find_elements(by, sel)
        if els:
            return els[0]
    return None

def click_or_go(driver, locators, label, fallback_url):

    before = driver.current_url
    el = find_first(driver, locators)
    if el:
        driver.execute_script("arguments[0].scrollIntoView({block:'center'});", el)
        js_click(driver, el, label)
        t0 = time.time()
        while time.time() - t0 < 0.7:
            if driver.current_url != before:
                return
            time.sleep(0.05)
        print(f"↪️ URL didn’t change; go → {fallback_url}")
        driver.get(fallback_url)
    else:
        print(f"↪️ Direct go (not found): {fallback_url}")
        driver.get(fallback_url)

def go_home_via_logo(driver):
    click_or_go(
        driver,
        [
            (By.CSS_SELECTOR, "header.header a.logo"),
            (By.XPATH, "//header//a[contains(@class,'logo')]"),
            (By.XPATH, "//header//a[normalize-space()='Home']"),
            (By.XPATH, "//header//a[@href='/' or @href='/home/' or contains(@href,'/')]"),
        ],
        "Header: Home/Logo",
        HOME_URL
    )

    t0 = time.time()
    while time.time() - t0 < 1.2:
        if is_home(driver.current_url):
            break
        time.sleep(0.05)
    print("🏠 Back on Home")


def show_home_and_scroll(driver):
    print("\n===== HOME: open and scroll top → bottom =====")
    driver.get(HOME_URL)
    try: WebDriverWait(driver, WAIT).until(lambda d: is_home(d.current_url))
    except TimeoutException: pass

    sections = [
        ("header.header", "Header"),
        ("section.hero", "Hero"),
        ("#mission-vision, section.mission-vision", "Mission & Vision"),
        ("section.showcase, #showcase", "Showcase / Technologies"),
        ("section.features, .features", "How It Works / Features"),
        ("section.team, .team", "Team"),
        ("section.testimonials, .testimonials", "Testimonials"),
        ("section.contact, #contact, .contact", "Contact"),
        ("footer", "Footer"),
    ]
    for css, label in sections:
        try:
            driver.execute_script("const el=document.querySelector(arguments[0]); if(el){ el.scrollIntoView({block:'center'}); }", css)
            print(f"↧ Scrolled to: {label}")
            time.sleep(0.08)
        except Exception:
            print(f"… Couldn’t scroll: {label}")

def home_contact_form_submit(driver):
    print("\n===== HOME: contact form submit =====")
    # ensure we’re near the form
    driver.execute_script("const f=document.querySelector('form.contact-form'); if(f){ f.scrollIntoView({block:'center'}); }")
    try:
        form = WebDriverWait(driver, 2).until(EC.presence_of_element_located((By.CSS_SELECTOR, "form.contact-form")))
    except TimeoutException:
        print("ℹ️ Contact form not found — skipping")
        return

    try:
        name  = form.find_element(By.NAME, "name")
        email = form.find_element(By.NAME, "email")
        msg   = form.find_element(By.NAME, "message")
        print("⌨️ Fill: Name")
        type_slow(name,  "QA Robot")
        print("⌨️ Fill: Email")
        type_slow(email, f"qa+{int(time.time())}@example.com")
        print("⌨️ Fill: Message")
        type_slow(msg,   "Hello from automated test — home contact form.")

        btn = form.find_element(By.CSS_SELECTOR, "button[type='submit']")
        js_click(driver, btn, "Submit Contact Form")
        print("✅ Submitted (no toast check)")
        time.sleep(0.3)
    except Exception as e:
        print(f"⚠️ Contact form fill/submit failed: {e}")

def about_page_scroll(driver):
    print("\n===== ABOUT: scroll page =====")

    anchors = [
        ("header.header", "Header"),
        ("main, .wrap, .container, .content, body", "Body Top"),
        ("h1,h2,h3", "Headings area"),
        ("footer", "Footer"),
    ]
    for css, label in anchors:
        try:
            driver.execute_script("const el=document.querySelector(arguments[0]); if(el){ el.scrollIntoView({block:'center'}); }", css)
            print(f"↧ Scrolled to: {label}")
            time.sleep(0.08)
        except Exception:
            pass

def header_nav_sequence(driver):
    print("\n===== HEADER NAV: About → Home → Contact → Home → Signup → Home → Login → Home =====")

    # About
    click_or_go(driver, [
        (By.XPATH, "//ul[contains(@class,'nav-links')]//a[contains(@href,'/users/about/')]"),
        (By.XPATH, "//header//a[normalize-space()='About']"),
        (By.XPATH, "//header//a[contains(@href,'/users/about/')]"),
    ], "Header: About", ABOUT_URL)
    about_page_scroll(driver)
    go_home_via_logo(driver)


    click_or_go(driver, [
        (By.XPATH, "//ul[contains(@class,'nav-links')]//a[contains(@href,'/users/contact/')]"),
        (By.XPATH, "//header//a[normalize-space()='Contact']"),
        (By.XPATH, "//header//a[contains(@href,'/users/contact/')]"),
    ], "Header: Contact", CONTACT_URL)
    go_home_via_logo(driver)


    click_or_go(driver, [
        (By.XPATH, "//ul[contains(@class,'nav-links')]//a[contains(@href,'/users/signup/')]"),
        (By.XPATH, "//header//a[normalize-space()='Signup']"),
        (By.XPATH, "//header//a[contains(@href,'/users/signup/')]"),
    ], "Header: Signup", SIGNUP_URL)
    go_home_via_logo(driver)


    click_or_go(driver, [
        (By.XPATH, "//ul[contains(@class,'nav-links')]//a[contains(@href,'/users/login/')]"),
        (By.XPATH, "//header//a[normalize-space()='Login']"),
        (By.XPATH, "//header//a[contains(@href,'/users/login/')]"),
    ], "Header: Login", LOGIN_URL)
    go_home_via_logo(driver)


if __name__ == "__main__":
    opts = webdriver.ChromeOptions()
    opts.page_load_strategy = "eager"  # faster
    opts.add_argument("--disable-renderer-backgrounding")
    opts.add_argument("--disable-features=PaintHolding")
    # opts.add_argument("--headless=new")  # optional

    driver = webdriver.Chrome(options=opts)
    driver.set_window_size(1360, 900)

    try:

        show_home_and_scroll(driver)


        home_contact_form_submit(driver)


        header_nav_sequence(driver)

        print("\n✅ Flow complete.")
    finally:
        driver.quit()
        print("🚪 Browser closed.")
