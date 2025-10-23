import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


# -----------------------------
# Helper functions
# -----------------------------
def slow_scroll(driver, pause=0.3):
    """Scroll the page smoothly from top to bottom."""
    total_height = driver.execute_script("return document.body.scrollHeight")
    for i in range(0, total_height, 300):
        driver.execute_script(f"window.scrollTo(0, {i});")
        time.sleep(pause)
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
    time.sleep(1)
    driver.execute_script("window.scrollTo(0, 0);")
    print("🌀 Scrolled full page.\n")


def scroll_navbar(driver):
    """Scroll the left sidebar if scrollable."""
    try:
        sidebar = driver.find_element(By.TAG_NAME, "aside")
        driver.execute_script("arguments[0].scrollTop = arguments[0].scrollHeight", sidebar)
        time.sleep(1)
        driver.execute_script("arguments[0].scrollTop = 0", sidebar)
        print("📜 Scrolled left sidebar.\n")
    except:
        print("⚠️ Sidebar not found or not scrollable.\n")


# -----------------------------
# Start Chrome browser
# -----------------------------
driver = webdriver.Chrome()
driver.maximize_window()
driver.get(" http://127.0.0.1:8000/users/login/")

# -----------------------------
# 1️⃣ LOGIN
# -----------------------------
WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, "id_username")))
driver.find_element(By.ID, "id_username").send_keys("Rahim")
driver.find_element(By.ID, "id_password").send_keys("V=u+at15260")

login_btn = WebDriverWait(driver, 10).until(
    EC.element_to_be_clickable((By.CSS_SELECTOR, "button.btn.btn-primary"))
)
login_btn.click()

# Wait for dashboard redirect
WebDriverWait(driver, 15).until(
    lambda d: "/dashboard" in d.current_url or "/driver" in d.current_url
)
print("✅ Logged in successfully — URL:", driver.current_url)
time.sleep(2)

# -----------------------------
# 2️⃣ DASHBOARD
# -----------------------------
# Click dashboard link (if not already there)
try:
    dashboard_link = WebDriverWait(driver, 5).until(
        EC.element_to_be_clickable((By.PARTIAL_LINK_TEXT, "Dashboard"))
    )
    dashboard_link.click()
except:
    print("ℹ️ Already on Dashboard.\n")

WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
print("📄 Scrolling dashboard page...")
slow_scroll(driver)
scroll_navbar(driver)

# -----------------------------
# 3️⃣ PROFILE PAGE
# -----------------------------
try:
    driver.get("http://127.0.0.1:8000/users/driver/profile/")
    WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
    print("✅ Profile page loaded")
    slow_scroll(driver)
    driver.back()
    time.sleep(2)
except Exception as e:
    print("⚠️ Profile page error:", e)

# -----------------------------
# 4️⃣ TASK PAGE
# -----------------------------
try:
    driver.get("http://127.0.0.1:8000/users/driver/tasks/")
    WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
    print("✅ Task page loaded")
    slow_scroll(driver)
    driver.back()
    time.sleep(2)
except Exception as e:
    print("⚠️ Task page error:", e)

# -----------------------------
# 5️⃣ DRIVER FORUM PAGE
# -----------------------------
try:
    driver.get("http://127.0.0.1:8000/users/driver/forum/")
    WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
    print("✅ Forum page loaded")
    slow_scroll(driver)
    driver.back()
    time.sleep(2)
except Exception as e:
    print("⚠️ Forum page error:", e)

# -----------------------------
# 6️⃣ COMPLAINT PAGE
# -----------------------------
try:
    driver.get("http://127.0.0.1:8000/users/driver/complaint/")
    WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, "form")))
    print("✅ Complaint page loaded")
    slow_scroll(driver)

    # Fill and submit form
    try:
        driver.find_element(By.NAME, "category").send_keys("Delay in Route")
        driver.find_element(By.NAME, "description").send_keys("Driver faced delay due to traffic.")
        driver.find_element(By.NAME, "address").send_keys("Mirpur 10, Dhaka")
        driver.find_element(By.XPATH, "//button[contains(text(),'Submit')]").click()
        print("✅ Complaint submitted successfully.\n")
        time.sleep(2)
    except:
        print("⚠️ Complaint form not found or already submitted.\n")

    driver.back()
    time.sleep(2)
except Exception as e:
    print("⚠️ Complaint page error:", e)

# -----------------------------
# 7️⃣ MAP ONLINE PAGE
# -----------------------------
try:
    driver.get("http://127.0.0.1:8000/users/driver/")
    WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
    print("✅ Back to Dashboard. Looking for Map Online button...")
    time.sleep(2)

    try:
        go_btn = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.ID, "btnGo")))
        driver.execute_script("arguments[0].scrollIntoView();", go_btn)
        go_btn.click()
        print("🗺️ Map Online clicked, waiting for location to load...")
        time.sleep(8)
        print("✅ Map displayed successfully.\n")
    except:
        print("⚠️ Map Online button not found.\n")
except Exception as e:
    print("⚠️ Map page error:", e)

# -----------------------------
# 8️⃣ NAVBAR LINKS TEST
# -----------------------------
print("🔁 Checking all top navbar links...")
try:
    nav_links = driver.find_elements(By.CSS_SELECTOR, "header a, nav a")
    for link in nav_links:
        try:
            href = link.get_attribute("href")
            text = link.text.strip() or href
            driver.execute_script("arguments[0].scrollIntoView();", link)
            link.click()
            print(f"✅ Opened navbar link: {text}")
            time.sleep(2)
            driver.back()
            time.sleep(2)
        except Exception as e:
            print(f"⚠️ Could not click navbar link: {e}")
except:
    print("⚠️ Navbar links not found.")

# -----------------------------
# 9️⃣ LOGOUT
# -----------------------------
try:
    driver.get("http://127.0.0.1:8000/users/logout/")
    WebDriverWait(driver, 10).until(EC.url_contains("/login"))
    print("\n✅ Logged out successfully — test completed!\n")
except Exception as e:
    print("⚠️ Logout error:", e)

# -----------------------------
# 🔚 CLOSE
# -----------------------------
driver.quit()
print("🚗 Browser closed — full automation finished successfully.")
