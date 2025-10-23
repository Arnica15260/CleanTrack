from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, ElementClickInterceptedException, NoSuchElementException
import time

# --- CONFIGURATION ---
USERNAME = "Rahim"
PASSWORD = "V=u+at15260"
COMPLAINT_TEXT = "This is a test complaint submitted via automation script."

SCROLL_DELAY = 0.05  # seconds between scrolls
SCROLL_STEP = 15     # pixels per scroll step


# --- FUNCTIONS ---

def slow_scroll(driver):
    """Scroll slowly from top to bottom of the page."""
    last_height = driver.execute_script("return document.body.scrollHeight")
    for i in range(0, last_height, SCROLL_STEP):
        driver.execute_script(f"window.scrollTo(0, {i});")
        time.sleep(SCROLL_DELAY)
    driver.execute_script(f"window.scrollTo(0, {last_height});")
    time.sleep(0.5)


def slow_sidebar_scroll(driver, sidebar_selector):
    """Scroll the left sidebar slowly."""
    try:
        sidebar = driver.find_element(By.CSS_SELECTOR, sidebar_selector)
        driver.execute_script("arguments[0].scrollTop = 0;", sidebar)
        height = driver.execute_script("return arguments[0].scrollHeight", sidebar)
        for i in range(0, height, SCROLL_STEP):
            driver.execute_script("arguments[0].scrollTop = arguments[1];", sidebar, i)
            time.sleep(SCROLL_DELAY)
        driver.execute_script("arguments[0].scrollTop = arguments[1];", sidebar, height)
        print("📜 Scrolled sidebar completely.")
    except Exception:
        print("⚠️ Sidebar scroll failed (not found or not scrollable).")
    time.sleep(0.5)


def safe_click(driver, element):
    """Safely click an element, retry if intercepted."""
    try:
        element.click()
        time.sleep(1)
        return True
    except ElementClickInterceptedException:
        driver.execute_script("arguments[0].scrollIntoView(true);", element)
        time.sleep(0.5)
        try:
            element.click()
            time.sleep(1)
            return True
        except Exception:
            return False


# --- START BROWSER ---
driver = webdriver.Chrome()
driver.maximize_window()

try:
    # --- LOGIN ---
    driver.get(" http://127.0.0.1:8000/users/login/")
    WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, "form")))

    # detect username/email field
    try:
        user_field = driver.find_element(By.NAME, "username")
    except NoSuchElementException:
        user_field = driver.find_element(By.NAME, "email")
    user_field.send_keys(USERNAME)

    # detect password field
    pwd_field = driver.find_element(By.NAME, "password")
    pwd_field.send_keys(PASSWORD)

    # try clicking the submit button (button or input)
    try:
        login_btn = driver.find_element(By.XPATH, "//button[contains(.,'Login') or contains(.,'Sign In') or contains(.,'Submit')]")
    except NoSuchElementException:
        login_btn = driver.find_element(By.XPATH, "//input[@type='submit' or @value='Login' or @value='Sign In']")

    safe_click(driver, login_btn)
    WebDriverWait(driver, 10).until(EC.url_contains("/dashboard/"))
    print(f"✅ Logged in successfully — URL: {driver.current_url}")

    # --- DASHBOARD ---
    slow_scroll(driver)
    slow_sidebar_scroll(driver, ".left-sidebar")
    print("🌀 Scrolled dashboard page and sidebar completely.")

    # --- PROFILE PAGE ---
    driver.get("http://127.0.0.1:8000/users/driver/profile/")
    WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
    slow_scroll(driver)
    print("✅ Loaded profile page and scrolled completely.")

    # --- TASK PAGE ---
    driver.get("http://127.0.0.1:8000/users/driver/tasks/")
    WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
    slow_scroll(driver)
    print("✅ Loaded tasks page and scrolled completely.")

    # --- FORUM PAGE ---
    driver.get("http://127.0.0.1:8000/users/driver/forum/")
    WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
    slow_scroll(driver)
    print("✅ Loaded forum page and scrolled completely.")

    # --- COMPLAINT PAGE ---
    driver.get("http://127.0.0.1:8000/users/driver/complaint/")
    WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.NAME, "complaint")))
    slow_scroll(driver)

    # Fill complaint form
    complaint_input = driver.find_element(By.NAME, "complaint")
    complaint_input.clear()
    complaint_input.send_keys(COMPLAINT_TEXT)

    submit_btn = driver.find_element(By.XPATH, "//button[contains(.,'Submit') or @type='submit']")
    if safe_click(driver, submit_btn):
        print("✅ Complaint submitted successfully.")
    else:
        print("⚠️ Complaint submission failed.")

    # --- MAP ONLINE PAGE ---
    try:
        driver.get("http://127.0.0.1:8000/users/driver/map/")
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
        slow_scroll(driver)
        print("🗺️ Map Online page loaded and scrolled completely.")
    except Exception as e:
        print(f"⚠️ Map Online failed: {e}")

    # --- NAVBAR BUTTONS ---
    print("🔁 Clicking navbar buttons...")
    nav_selectors = "header a, nav a"
    nav_links_count = len(driver.find_elements(By.CSS_SELECTOR, nav_selectors))
    for i in range(nav_links_count):
        try:
            nav_links = driver.find_elements(By.CSS_SELECTOR, nav_selectors)
            link = nav_links[i]
            href = link.get_attribute("href") or link.text
            safe_click(driver, link)
            time.sleep(2)
            slow_scroll(driver)
            print(f"✅ Opened navbar link: {href}")
            driver.back()
            time.sleep(2)
        except Exception as e:
            print(f"⚠️ Could not click navbar link: {e}")

    # --- LOGOUT ---
    try:
        logout_btn = driver.find_element(By.XPATH, "//a[contains(.,'Logout')]")
        if safe_click(driver, logout_btn):
            print("✅ Logged out successfully.")
        else:
            print("⚠️ Logout failed.")
    except Exception:
        print("⚠️ Logout button not found.")

finally:
    time.sleep(2)
    driver.quit()
    print("🚗 Browser closed — full automation finished successfully.")
