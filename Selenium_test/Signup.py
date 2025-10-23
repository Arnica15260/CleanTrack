
import time, re
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

BASE_URL = ""
SIGNUP_URL = f"{BASE_URL}/users/signup/"
LOGIN_URL  = f"{BASE_URL}/users/login/"

WAIT = 12

driver = webdriver.Chrome()
driver.set_window_size(1200, 900)

def wait_vis(by, sel, timeout=WAIT):
    return WebDriverWait(driver, timeout).until(EC.visibility_of_element_located((by, sel)))

def highlight(el, color="#ffeb3b"):
    driver.execute_script("arguments[0].style.outline='3px solid %s';" % color, el)

def slow_type(el, text, delay=0.08):
    el.clear()
    highlight(el)
    for ch in text:
        el.send_keys(ch); time.sleep(delay)

def try_send_keys(locators, value):
    for by, sel in locators:
        try:
            el = WebDriverWait(driver, 3).until(EC.visibility_of_element_located((by, sel)))
            slow_type(el, value)
            return True
        except Exception:
            continue
    return False

def make_bd_phone(seed):
    return f"+88017{(seed + '00000000')[:8]}"

try:

    driver.get(f"{BASE_URL}/users/logout/")
    driver.delete_all_cookies()
    time.sleep(0.3)

    driver.get(SIGNUP_URL)

    stamp = datetime.now().strftime("%Y%m%d%H%M%S")
    username = f"auto_user_{stamp}"
    email    = f"{username}@example.com"
    password = "Passw0rd!234"
    phone    = make_bd_phone(stamp[-8:])

    slow_type(wait_vis(By.NAME, "username"), username)
    slow_type(wait_vis(By.NAME, "email"), email)
    slow_type(wait_vis(By.NAME, "password1"), password)
    slow_type(wait_vis(By.NAME, "password2"), password)


    try_send_keys([
        (By.NAME, "phone_number"),
        (By.NAME, "phone"),
        (By.NAME, "mobile"),
        (By.CSS_SELECTOR, "input[type='tel']"),
        (By.CSS_SELECTOR, "input[name*='phone' i]"),
    ], phone)

    # submit
    submit = wait_vis(By.CSS_SELECTOR, "button[type='submit'],input[type='submit']")
    highlight(submit, "#80deea"); time.sleep(0.2)
    submit.click()
    print("📝 Signup submitted")


    try:
        WebDriverWait(driver, WAIT).until(EC.url_contains("/users/login/"))
        print("➡️ Redirected to login after signup")
    except TimeoutException:
        print("⚠️ Not redirected to login. Current:", driver.current_url)


    msg_text = (driver.page_source or "").lower()
    for sel in [".messages li", ".alert", "ul.messagelist li"]:
        for e in driver.find_elements(By.CSS_SELECTOR, sel):
            msg_text += " " + e.text.lower()
    if "activate" in msg_text or "activation" in msg_text:
        print("✅ Activation message shown")
    else:
        print("ℹ️ No activation message found (check your template/messages)")


    out = f"signup_demo_{stamp}.png"
    driver.save_screenshot(out)
    print("📸 Saved:", out)

finally:
    time.sleep(10)
    driver.quit()
    print("🚪 Browser closed.")
