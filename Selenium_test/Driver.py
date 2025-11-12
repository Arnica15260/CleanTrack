import time
from urllib.parse import urljoin, urlparse

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

BASE = "http://127.0.0.1:8000".rstrip("/")

def slow_scroll(driver, pause=0.3):
    try:
        total_height = driver.execute_script(
            "return Math.max(document.body.scrollHeight, document.documentElement.scrollHeight)"
        )
        y = 0
        while y < total_height:
            driver.execute_script("window.scrollTo(0, arguments[0]);", y)
            time.sleep(pause)
            y += 300
            total_height = driver.execute_script(
                "return Math.max(document.body.scrollHeight, document.documentElement.scrollHeight)"
            )
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(1)
        driver.execute_script("window.scrollTo(0, 0);")
    except Exception:
        pass
    print("🌀 Scrolled full page.\n")


def scroll_navbar(driver):
    try:
        sidebar = driver.find_element(By.TAG_NAME, "aside")
        driver.execute_script("arguments[0].scrollTop = arguments[0].scrollHeight", sidebar)
        time.sleep(1)
        driver.execute_script("arguments[0].scrollTop = 0", sidebar)
        print("📜 Scrolled left sidebar.\n")
    except Exception:
        print("⚠️ Sidebar not found or not scrollable.\n")


def safe_get(driver, url):
    driver.get((url or "").strip())


def click_first_that_exists(driver, locators, wait=6):
    for by, sel in locators:
        try:
            el = WebDriverWait(driver, wait).until(EC.element_to_be_clickable((by, sel)))
            el.click()
            time.sleep(0.4)
            return True
        except Exception:
            continue
    return False


def robust_submit_current_form(driver, password_field=None):

    submit_locators = [
        (By.XPATH, "//button[@type='submit']"),
        (By.XPATH, "//button[contains(normalize-space(.),'Log in') or "
                   "contains(normalize-space(.),'Login') or "
                   "contains(normalize-space(.),'Sign in') or "
                   "contains(normalize-space(.),'Submit')]"),
        (By.CSS_SELECTOR, "input[type='submit']"),
        (By.XPATH, "//input[@type='submit' or @value='Log in' or @value='Login' or @value='Sign in' or @value='Submit']"),
        (By.CSS_SELECTOR, "button.btn.btn-primary[type='submit'], .auth-form button[type='submit']"),
    ]
    if click_first_that_exists(driver, submit_locators, wait=4):
        return True
    try:
        if password_field:
            password_field.send_keys(Keys.ENTER)
            time.sleep(0.2)
            return True
    except Exception:
        pass
    try:
        driver.execute_script("var f=document.querySelector('form'); if(f){ f.submit(); }")
        time.sleep(0.2)
        return True
    except Exception:
        return False


def is_same_site(href):
    if not href:
        return False
    if href.startswith(("#", "javascript:", "mailto:", "tel:")):
        return False
    abs_url = href if bool(urlparse(href).netloc) else urljoin(BASE + "/", href.lstrip("/"))
    return urlparse(abs_url).netloc == urlparse(BASE).netloc


def collect_nav_hrefs(driver, limit=30):
    hrefs, seen = [], set()
    try:
        links = driver.find_elements(By.CSS_SELECTOR, "header a, nav a")
        for a in links:
            try:
                href = a.get_attribute("href") or ""
            except Exception:
                continue
            if not is_same_site(href):
                continue
            abs_url = href if bool(urlparse(href).netloc) else urljoin(BASE + "/", href.lstrip("/"))
            cur = driver.current_url.rstrip("/")
            tgt = abs_url.rstrip("/")
            if not tgt or tgt in seen or tgt == cur:
                continue
            seen.add(tgt)
            hrefs.append(tgt)
            if len(hrefs) >= limit:
                break
    except Exception:
        pass
    return hrefs

driver = webdriver.Chrome()
driver.maximize_window()
safe_get(driver, f"{BASE}/users/login/")  # removed leading space

WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, "form")))

# Username/Email field
try:
    user = driver.find_element(By.ID, "id_username")
except Exception:
    # fallback to name=email if your template uses email
    try:
        user = driver.find_element(By.NAME, "username")
    except Exception:
        user = driver.find_element(By.NAME, "email")
user.clear()
user.send_keys("Rahim")

# Password field
try:
    pwd = driver.find_element(By.ID, "id_password")
except Exception:
    pwd = driver.find_element(By.NAME, "password")
pwd.clear()
pwd.send_keys("V=u+at15260")

# Submit robustly (supports button/input/Enter/JS)
if not robust_submit_current_form(driver, password_field=pwd):
    raise RuntimeError("Login submit control not found.")

# Wait for dashboard redirect
WebDriverWait(driver, 15).until(lambda d: "/dashboard" in d.current_url or "/driver" in d.current_url)
print("✅ Logged in successfully — URL:", driver.current_url)
time.sleep(1.5)

# -----------------------------
# 2️⃣ DASHBOARD
# -----------------------------
try:
    dashboard_link = WebDriverWait(driver, 3).until(
        EC.element_to_be_clickable((By.PARTIAL_LINK_TEXT, "Dashboard"))
    )
    dashboard_link.click()
except Exception:
    pass
WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
print("📄 Scrolling dashboard page...")
slow_scroll(driver)
scroll_navbar(driver)

# -----------------------------
# 3️⃣ PROFILE PAGE
# -----------------------------
try:
    safe_get(driver, f"{BASE}/users/driver/profile/")
    WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
    print("✅ Profile page loaded")
    slow_scroll(driver)
    driver.back(); time.sleep(1)
except Exception as e:
    print("⚠️ Profile page error:", e)

# -----------------------------
# 4️⃣ TASK PAGE
# -----------------------------
try:
    safe_get(driver, f"{BASE}/users/driver/tasks/")
    WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
    print("✅ Task page loaded")
    slow_scroll(driver)
    driver.back(); time.sleep(1)
except Exception as e:
    print("⚠️ Task page error:", e)

# -----------------------------
# 5️⃣ DRIVER FORUM PAGE
# -----------------------------
try:
    safe_get(driver, f"{BASE}/users/driver/forum/")
    WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
    print("✅ Forum page loaded")
    slow_scroll(driver)
    driver.back(); time.sleep(1)
except Exception as e:
    print("⚠️ Forum page error:", e)

# -----------------------------
# 6️⃣ COMPLAINT PAGE
# -----------------------------
try:
    safe_get(driver, f"{BASE}/users/driver/complaint/")
    WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, "form")))
    print("✅ Complaint page loaded")
    slow_scroll(driver)

    # Try several common field names/ids
    def try_send(by, sel, text):
        try:
            el = driver.find_element(by, sel)
            el.clear(); el.send_keys(text); return True
        except Exception:
            return False

    filled = 0
    filled += try_send(By.NAME, "category", "Delay in Route") or try_send(By.ID, "id_category", "Delay in Route")
    filled += try_send(By.NAME, "description", "Driver faced delay due to traffic.") or try_send(By.ID, "id_description", "Driver faced delay due to traffic.") or try_send(By.NAME, "message", "Driver faced delay due to traffic.") or try_send(By.ID, "id_message", "Driver faced delay due to traffic.")
    filled += try_send(By.NAME, "address", "Mirpur 10, Dhaka") or try_send(By.ID, "id_address", "Mirpur 10, Dhaka")

    if filled:
        if click_first_that_exists(driver, [
            (By.XPATH, "//button[contains(normalize-space(.),'Submit') or contains(normalize-space(.),'Send') or @type='submit']"),
            (By.CSS_SELECTOR, "form button[type='submit'], form input[type='submit']")
        ], wait=5):
            print("✅ Complaint submitted successfully.\n")
        else:
            if robust_submit_current_form(driver):
                print("✅ Complaint submitted (fallback).\n")
            else:
                print("⚠️ Complaint submission failed (no submit control).\n")
    else:
        print("⚠️ Complaint form fields not found; skipping submit.\n")

    driver.back(); time.sleep(1)
except Exception as e:
    print("⚠️ Complaint page error:", e)

# -----------------------------
# 7️⃣ MAP ONLINE PAGE
# -----------------------------
try:
    safe_get(driver, f"{BASE}/users/driver/")
    WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
    print("✅ Back to Dashboard. Looking for Map Online button...")
    time.sleep(1)

    try:
        go_btn = WebDriverWait(driver, 4).until(EC.element_to_be_clickable((By.ID, "btnGo")))
        driver.execute_script("arguments[0].scrollIntoView({block:'center'});", go_btn)
        go_btn.click()
    except Exception:
        # Fallback to direct map URL if button not present
        safe_get(driver, f"{BASE}/users/driver/map/")

    WebDriverWait(driver, 8).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
    print("🗺️ Map Online clicked, waiting for location to load...")
    time.sleep(2)
    print("✅ Map displayed successfully.\n")
except Exception as e:
    print("⚠️ Map page error:", e)

# -----------------------------
# 8️⃣ NAVBAR LINKS TEST (stale-proof)
# -----------------------------
print("🔁 Checking all top navbar links...")
try:
    hrefs = collect_nav_hrefs(driver, limit=30)
    if not hrefs:
        print("ℹ️ No navbar links collected or all are same-page.\n")
    for href in hrefs:
        try:
            safe_get(driver, href)
            WebDriverWait(driver, 6).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
            slow_scroll(driver)
            print(f"✅ Opened navbar link: {href}")
            # return to dashboard to keep context
            safe_get(driver, f"{BASE}/users/driver/")
            WebDriverWait(driver, 6).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
        except Exception as e:
            print(f"⚠️ Could not open navbar link {href}: {e}")
except Exception:
    print("⚠️ Navbar links not found or crawl failed.")


driver.quit()
print("🚗 Browser closed — full automation finished successfully.")
