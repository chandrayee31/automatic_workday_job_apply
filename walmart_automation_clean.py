import os
import time
from pathlib import Path

from dotenv import load_dotenv
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

# --------------------------------------------------
# Load environment variables
# --------------------------------------------------
load_dotenv()

WORKDAY_URL = os.getenv("WORKDAY_URL")
USERNAME = os.getenv("WORKDAY_USER")
PASSWORD = os.getenv("WORKDAY_PASS")
JOB_IDS = [j.strip() for j in os.getenv("JOB_IDS", "").split(",") if j.strip()]

LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)

# --------------------------------------------------
# Job Tracking Lists
# --------------------------------------------------
SUCCESSFUL_SUBMISSIONS = []
FAILED_SUBMISSIONS = []
INCOMPLETE_SUBMISSIONS = []

# --------------------------------------------------
# Predefined Answers for Application Questions
# --------------------------------------------------
APPLICATION_ANSWERS = [
    "Yes",  # Question 1: Do you certify you meet all minimum qualifications
    "Opt-Out from receiving text messages from Walmart",  # Question 2: Message and data rates
    "Yes",  # Question 3: Are you legally able to work in the country
    "18 years of age and Over",  # Question 4: Please select your age category
    "Previous associate",  # Question 5: Please select your Walmart Associate Status
    "Yes",  # Question 6: Are you able to provide work authorization within 3 days
    "No",   # Question 7: Will you now or in the future require sponsorship
    "No",   # Question 8: Do you have Active Duty or Guard/Reserve experience
    "No",   # Question 9: Are you the Spouse/Partner of someone in the Uniformed Services
    "No",   # Question 10: Do you have a direct family member who currently works for Walmart
]

VOLUNTARY_DISCLOSURE_ANSWERS = [
    "Asian/No Hispanic Origin (United States of America)",  # Ethnicity
    "Female",  # Gender
]

# --------------------------------------------------
# Utility Functions
# --------------------------------------------------
def debug_screenshot(page, name: str):
    """Take a screenshot for debugging purposes."""
    try:
        page.screenshot(path=str(LOG_DIR / f"{name}.png"), full_page=True)
        print(f"📸 Screenshot saved: {name}.png")
    except Exception as e:
        print(f"⚠ Could not take screenshot: {e}")


def wait_for_page_load(page, timeout=10000):
    """Wait for page to load completely."""
    try:
        page.wait_for_load_state("networkidle", timeout=timeout)
        time.sleep(4)
    except Exception as e:
        print(f"⚠ Page load timeout: {e}")


# --------------------------------------------------
# STEP 1: Login to Workday
# --------------------------------------------------
def step_1_login(page):
    """
    Step 1: Log into Workday system
    """
    print("\n🔹 STEP 1: Logging into Workday...")
    
    # Navigate to login page
    page.goto(WORKDAY_URL, wait_until="networkidle")
    time.sleep(2)
    debug_screenshot(page, "step_1_login_page")
    
    # Fill username
    print("   Filling username...")
    page.fill('input[id="input-4"]', USERNAME)
    
    # Fill password
    print("   Filling password...")
    page.fill('input[id="input-5"]', PASSWORD)
    
    # Click Sign In button
    print("   Clicking Sign In button...")
    page.click('[data-automation-id="signInSubmitButton"]', force=True)
    
    # Wait for login to complete
    wait_for_page_load(page)
    debug_screenshot(page, "step_1_after_login")
    print("✅ STEP 1 COMPLETED: Successfully logged in")


# --------------------------------------------------
# STEP 2: Navigate to Job Search
# --------------------------------------------------
def step_2_navigate_to_jobs(page):
    """
    Step 2: Navigate to job search page
    """
    print("\n🔹 STEP 2: Navigating to job search...")
    
    page.goto("https://walmart.wd5.myworkdayjobs.com/en-US/WalmartExternal", wait_until="networkidle")
    time.sleep(3)
    debug_screenshot(page, "step_2_job_search_page")
    print("✅ STEP 2 COMPLETED: Reached job search page")


# --------------------------------------------------
# STEP 3: Search for Specific Job
# --------------------------------------------------
def step_3_search_job(page, job_id: str):
    """
    Step 3: Search for a specific job by ID
    """
    print(f"\n🔹 STEP 3: Searching for job {job_id}...")
    
    # Find search box
    search_box = page.locator('input[type="text"]').first
    
    # Search for job
    print(f"   Searching for job ID: {job_id}")
    search_box.click()
    search_box.fill(job_id)
    search_box.press("Enter")
    
    wait_for_page_load(page)
    debug_screenshot(page, "step_3_search_results")
    
    # Click on the job result
    print("   Clicking on job result...")
    job_link = page.locator(f'a[href*="{job_id}"]').first
    job_link.click()
    
    wait_for_page_load(page)
    debug_screenshot(page, "step_3_job_page")
    print("✅ STEP 3 COMPLETED: Opened job page")


# --------------------------------------------------
# STEP 4: Click Apply Button
# --------------------------------------------------
def step_4_click_apply(page, job_id: str):
    """
    Step 4: Click Apply button and handle "Use last application"
    """
    print("\n🔹 STEP 4: Clicking Apply button...")
    
    # Try to find Apply or Continue Application button
    apply_selectors = [
        'a:has-text("Apply")',
        'button:has-text("Apply")',
        'a:has-text("Continue Application")',
        'button:has-text("Continue Application")',
        '[data-automation-id*="apply"]',
        '[data-automation-id*="continue"]'
    ]
    
    button_clicked = False
    for selector in apply_selectors:
        button = page.locator(selector).first
        if button.count() > 0 and button.is_visible():
            button.click()
            button_text = button.inner_text() if button.count() > 0 else "Apply"
            print(f"   Clicked {button_text} button")
            button_clicked = True
            break
    
    if not button_clicked:
        print("   ❌ No Apply or Continue Application button found - trying once more...")
        step_3_search_job(page, job_id=job_id)  # Retry searching for job ONCE
        
        # Try to find Apply button again after retry
        for selector in apply_selectors:
            button = page.locator(selector).first
            if button.count() > 0 and button.is_visible():
                button.click()
                button_text = button.inner_text() if button.count() > 0 else "Apply"
                print(f"   ✅ Found {button_text} button after retry")
                button_clicked = True
                break
        
        # If still not found after retry, give up
        if not button_clicked:
            print("   ❌ No Apply or Continue Application button found even after retry")
            debug_screenshot(page, f"no_apply_button_{job_id}")
            return False
    
    wait_for_page_load(page)
    debug_screenshot(page, "step_4_after_apply")
    
    # Look for "Use last application" button
    print("   Looking for 'Use last application' option...")
    try:
        use_last_app = page.locator('a:has-text("Use")').first
        if use_last_app.count() > 0:
            print("   Found 'Use last application' - clicking it...")
            use_last_app.click()
            wait_for_page_load(page)
            debug_screenshot(page, "step_4_used_last_app")
        else:
            print("   No 'Use last application' option found")
    except Exception as e:
        print(f"   Error with 'Use last application': {e}")
    
    print("✅ STEP 4 COMPLETED: Apply process initiated")


# --------------------------------------------------
# STEP 5: Handle My Information Page (1st Application Page)
# --------------------------------------------------
def step_5_my_information(page):
    """
    Step 5: Fill "How Did You Hear About Us?" question on My Information page
    """
    print("\n🔹 STEP 5: Handling My Information page...")
    
    debug_screenshot(page, "step_5_my_information")
    
    # Look for "How Did You Hear About Us?" question
    try:
        hear_about_selector = page.locator('text="How Did You Hear About Us?"')
        if hear_about_selector.count() > 0:
            print("   Found 'How Did You Hear About Us?' question")
            
            # Look for search box with placeholder "Search"
            search_box = page.locator('input[placeholder*="Search"]').first
            if search_box.count() > 0 and search_box.is_visible():
                print("   Filling search box with 'Walmart Career Site'")
                search_box.click()
                search_box.fill("Walmart Career Site")
                print("   Pressing Enter to search...")
                search_box.press("Enter")
                time.sleep(2)
        else:
            print("   'How Did You Hear About Us?' question not found, skipping...")
    except Exception as e:
        print(f"   Error handling question: {e}")
    
    # Click Save and Continue
    try:
        print("   Looking for Save and Continue button...")
        save_button = page.locator('button:has-text("Save and Continue")').first
        if save_button.count() > 0:
            save_button.click()
            wait_for_page_load(page)
    except Exception as e:
        print(f"   Error clicking Save and Continue: {e}")
    
    wait_for_page_load(page)
    debug_screenshot(page, "step_5_after_save")
    print("✅ STEP 5 COMPLETED: My Information page completed")


# --------------------------------------------------
# STEP 6: Handle My Experience Page (2nd Application Page)
# --------------------------------------------------
def step_6_my_experience(page):
    """
    Step 6: Simply click Save on My Experience page
    """
    print("\n🔹 STEP 6: Handling My Experience page...")
    
    debug_screenshot(page, "step_6_my_experience")
    
    # Just click Save and Continue
    print("   Clicking Save and Continue...")
    save_button = page.locator('button:has-text("Save and Continue")').first
    save_button.click()
    
    wait_for_page_load(page)
    debug_screenshot(page, "step_6_after_save")
    print("✅ STEP 6 COMPLETED: My Experience page completed")


# --------------------------------------------------
# STEP 7: Handle Application Questions Page (3rd Application Page)
# --------------------------------------------------
def step_7_application_questions(page):
    """
    Step 7: Fill dropdown questions on Application Questions page using pattern matching
    """
    print("\n🔹 STEP 7: Handling Application Questions page...")
    
    debug_screenshot(page, "step_7_application_questions")
    
    # Verify we're on the right page
    app_questions_text = page.locator('text="Application Questions"')
    if app_questions_text.count() > 0:
        print("✅ Confirmed: On Application Questions page")
        
        # Function to check if a dropdown is already filled
        def is_dropdown_filled(dropdown_element):
            """Check if a dropdown already has a value selected"""
            try:
                # Check for various indicators that dropdown is filled
                dropdown_text = dropdown_element.inner_text().lower()
                
                # Common indicators of unfilled dropdowns
                empty_indicators = [
                    "select one", "select an", "choose", "please select", 
                    "-- select", "select...", "click to select", ""
                ]
                
                # If dropdown text matches empty indicators, it's not filled
                if any(indicator in dropdown_text for indicator in empty_indicators):
                    return False
                
                # Check for aria attributes indicating selection
                aria_expanded = dropdown_element.get_attribute("aria-expanded")
                value = dropdown_element.get_attribute("value")
                
                # If it has a real value (not empty), it's probably filled
                if value and value.strip() and value not in ["", "0", "-1"]:
                    return True
                
                # If the text is longer than typical placeholder text, likely filled
                if len(dropdown_text.strip()) > 15:
                    return True
                    
                return False
            except Exception:
                return False

        # Function to find and fill question by pattern
        def fill_question_by_pattern(pattern_text, answer_text):
            """Find a question containing the pattern and fill it with the answer"""
            print(f"\n🔍 Looking for question containing: '{pattern_text}'")
            
            # Search for text containing the pattern in form-specific elements
            question_selectors = [
                f'fieldset:has-text("{pattern_text}")',
                f'legend:has-text("{pattern_text}")', 
                f'label:has-text("{pattern_text}")',
            ]
            
            found_valid_question = False
            
            for selector in question_selectors:
                try:
                    question_elements = page.locator(selector)
                    
                    for i in range(question_elements.count()):
                        try:
                            question_element = question_elements.nth(i)
                            if question_element.is_visible():
                                question_text = question_element.inner_text()[:150]
                                
                                # Skip navigation elements
                                if any(nav_term in question_text.lower() for nav_term in 
                                      ['skip to main', 'search for jobs', 'candidate home', 'settings', 'english', 'español']):
                                    continue
                                
                                # Check if this looks like a real form question
                                if len(question_text.strip()) > 10 and any(question_word in question_text.lower() for question_word in 
                                   ['?', 'select', 'certify', 'work', 'status', 'category', 'experience']):
                                    print(f"   ✅ Found valid question: {question_text}...")
                                    print(f"   📝 Answer to fill: {answer_text}")
                                    
                                    # Now find the dropdown/listbox below this question
                                    print(f"   🎯 Looking for dropdown to select answer...")
                                    
                                    # Look for dropdown in the same container and nearby containers
                                    for level in range(1, 4):  # Check parent, grandparent, etc.
                                        container = question_element.locator(f'xpath=ancestor::*[{level}]')
                                        
                                        dropdown_selectors = [
                                            '[role="combobox"]',
                                            'select', 
                                            '[aria-haspopup="listbox"]',
                                            'button[aria-expanded]',
                                            'button[aria-haspopup="listbox"]',
                                            'button:has-text("Select One")',
                                        ]
                                        
                                        for dropdown_selector in dropdown_selectors:
                                            dropdown = container.locator(dropdown_selector).first
                                            if dropdown.count() > 0 and dropdown.is_visible():
                                                try:
                                                    # Check if dropdown is already filled
                                                    if is_dropdown_filled(dropdown):
                                                        print(f"   ✅ Dropdown already filled - skipping")
                                                        found_valid_question = True
                                                        return True
                                                    
                                                    print(f"   📋 Found empty dropdown, clicking to open...")
                                                    dropdown.scroll_into_view_if_needed()
                                                    dropdown.click()
                                                    time.sleep(2)
                                                    
                                                    # Look for the answer option in the opened dropdown
                                                    option_selectors = [
                                                        f'[role="option"]:has-text("{answer_text}")',
                                                        f'li:has-text("{answer_text}")',
                                                        f'div:has-text("{answer_text}")',
                                                        f'[data-automation-label*="{answer_text}"]'
                                                    ]
                                                    
                                                    answer_found = False
                                                    for opt_selector in option_selectors:
                                                        option = page.locator(opt_selector).first
                                                        if option.count() > 0 and option.is_visible():
                                                            option.click()
                                                            print(f"   ✅ Successfully selected: {answer_text}")
                                                            time.sleep(1)
                                                            answer_found = True
                                                            found_valid_question = True
                                                            return True
                                                    
                                                    if not answer_found:
                                                        print(f"   ❌ Could not find answer option: {answer_text}")
                                                        # Try partial matching
                                                        words = answer_text.split()
                                                        for word in words:
                                                            if len(word) > 3:
                                                                partial_option = page.locator(f'[role="option"]:has-text("{word}")').first
                                                                if partial_option.count() > 0 and partial_option.is_visible():
                                                                    partial_option.click()
                                                                    print(f"   ✅ Selected partial match: {word}")
                                                                    found_valid_question = True
                                                                    return True
                                                        
                                                        page.keyboard.press('Escape')  # Close dropdown
                                                        return False
                                                        
                                                except Exception as e:
                                                    print(f"   ❌ Error with dropdown: {e}")
                                                    try:
                                                        page.keyboard.press('Escape')
                                                    except:
                                                        pass
                                    
                                    # If no dropdown found
                                    print(f"   ⚠️  Found question but no dropdown to fill")
                                    return False
                                else:
                                    print(f"   ⚠️  Found text but not a form question: {question_text[:50]}...")
                                    
                                    # SIMPLE HANDLER: Look for dropdown directly below this text
                                    print(f"   🔧 Looking for dropdown directly below this text...")
                                    
                                    # Look for dropdown that comes after/below this element
                                    dropdown_selectors = [
                                        '[role="combobox"]',
                                        'select', 
                                        '[aria-haspopup="listbox"]',
                                        'button[aria-expanded]',
                                        'button[aria-haspopup="listbox"]',
                                        'button:has-text("Select One")',
                                    ]
                                    
                                    # First try following siblings (elements that come after this one)
                                    for dropdown_selector in dropdown_selectors:
                                        # Look for dropdown as next sibling or following sibling
                                        following_dropdown = question_element.locator(f'xpath=following-sibling::{dropdown_selector.replace("[", "").replace("]", "")}').first
                                        if following_dropdown.count() == 0:
                                            # Try more general following siblings
                                            following_dropdown = question_element.locator(f'xpath=following-sibling::*').locator(dropdown_selector).first
                                        
                                        if following_dropdown.count() > 0 and following_dropdown.is_visible():
                                            try:
                                                print(f"   📋 Found dropdown below text, clicking to open...")
                                                following_dropdown.scroll_into_view_if_needed()
                                                following_dropdown.click()
                                                time.sleep(2)
                                                
                                                # Look for "No" option
                                                option = page.locator('[role="option"]:has-text("No")').first
                                                if option.count() > 0 and option.is_visible():
                                                    option.click()
                                                    print(f"   ✅ SUCCESS: Selected 'No' in dropdown below text")
                                                    time.sleep(1)
                                                    found_valid_question = True
                                                    return True
                                                else:
                                                    print(f"   ❌ Could not find 'No' option")
                                                    page.keyboard.press('Escape')
                                                    
                                            except Exception as e:
                                                print(f"   ❌ Error with dropdown below text: {e}")
                                                try:
                                                    page.keyboard.press('Escape')
                                                except:
                                                    pass
                                    
                                    print(f"   ❌ No dropdown found directly below this text")
                                
                        except Exception as e:
                            continue
                            
                except Exception as e:
                    continue
            
            if not found_valid_question:
                print(f"   ❌ Could not find valid form question with pattern: '{pattern_text}'")
            return False
        
        # Store the function for user to call
        page.fill_question_by_pattern = fill_question_by_pattern
        
        print("\n💡 Filling Application Questions with provided patterns...")
        
        # Question patterns and answers provided by user
        question_mappings = {
            "Do you certify you meet all minimum qualifications": "Yes",  # Fixed pattern
            "mobile text message": "Opt-Out from receiving text messages from Walmart",
            "Are you legally able to work": "Yes",
            "Please select your age category": "18 years of age and Over",
            "Walmart Associate Status": "Previous associate", 
            "work authorization within 3 days": "Yes",
            "sponsorship for an immigration-related employment": "No",
            # Fixed
            #  pattern for the service members hiring program question
            "Walmart in determining your eligibility": "No",
            

            # "uniformed": "No",
            "Spouse/Partner of someone": "No",
            "direct family member": "No"
            
        }
        
        # 🛑 STOPPING HERE - NO MORE QUESTION SEARCH TO PREVENT RE-FILLING
        print("🛑 STOPPING HERE - NO MORE QUESTION SEARCH TO PREVENT RE-FILLING")
        
        # Separate function for handling military question specifically
        def handle_military_question():
            """
            Special handler for the military hiring program question using regex patterns
            """
            import re
            print(f"\n🪖 MILITARY HANDLER: Looking for military hiring program question with regex")
            
            # Comprehensive regex patterns for military questions
            military_regex_patterns = [
                # Main hiring program question
                r'(active duty|guard|reserve|uniformed services)',
                r'(The following questions are to assist Walmart)',
                r'(Active Duty or Guard/Reserve experience in the Uniformed Services of the United States?)',
                
            ]
            
            # Convert patterns to case-insensitive
            compiled_patterns = [re.compile(pattern, re.IGNORECASE | re.DOTALL) for pattern in military_regex_patterns]
            
            # Get all visible text elements on the page
            all_text_elements = page.locator('*').all()
            
            for element in all_text_elements:
                try:
                    if not element.is_visible():
                        continue
                        
                    element_text = element.inner_text()
                    if len(element_text.strip()) < 20:  # Skip short text elements
                        continue
                    
                    # Check if any regex pattern matches this element
                    for i, pattern in enumerate(compiled_patterns):
                        if pattern.search(element_text):
                            print(f"   🎯 REGEX MATCH #{i+1}: Found military question pattern")
                            print(f"   📝 Matched text: {element_text[:200]}...")
                            print(f"   🔍 Pattern used: {military_regex_patterns[i]}")
                            
                            # Look for dropdown near this element
                            for level in range(1, 6):  # Check multiple parent levels
                                container = element.locator(f'xpath=ancestor::*[{level}]')
                                
                                # Search for dropdown ONLY in the same container as the military text
                                dropdown_selectors = [
                                    '[role="combobox"]',
                                    'select', 
                                    '[aria-haspopup="listbox"]',
                                    'button[aria-expanded]',
                                    'button[aria-haspopup="listbox"]',
                                    'button:has-text("Select One")',
                                    'button:has-text("Choose")',
                                    'button:has-text("Please select")'
                                ]
                                
                                # Only look for dropdowns in THIS specific container
                                for selector in dropdown_selectors:
                                    dropdowns = container.locator(selector)
                                    for j in range(dropdowns.count()):
                                        dropdown = dropdowns.nth(j)
                                        if dropdown.is_visible():
                                            try:
                                                dropdown_text = dropdown.inner_text().lower()
                                                print(f"   🔍 Found dropdown in military container: '{dropdown_text}'")
                                                
                                                # Check if it's not already filled with "No"
                                                if ("no" not in dropdown_text or 
                                                    "select" in dropdown_text or 
                                                    dropdown_text.strip() == ""):
                                                    
                                                    print(f"   🎯 Found military dropdown, filling with 'No'")
                                                    dropdown.scroll_into_view_if_needed()
                                                    dropdown.click()
                                                    time.sleep(2)
                                                    
                                                    # Try multiple ways to select "No"
                                                    no_option_selectors = [
                                                        '[role="option"]:has-text("No")',
                                                        'li:has-text("No")',
                                                        'div:has-text("No")',
                                                        '[data-automation-label="No"]',
                                                        'option[value="No"]',
                                                        '*:has-text("No"):not(:has(*))'  # Exact text match
                                                    ]
                                                    
                                                    for no_selector in no_option_selectors:
                                                        option = page.locator(no_selector).first
                                                        if option.count() > 0 and option.is_visible():
                                                            option.click()
                                                            print(f"   ✅ MILITARY REGEX SUCCESS: Selected 'No'")
                                                            time.sleep(1)
                                                            return True
                                                    
                                                    # If exact "No" not found, try partial matches
                                                    print(f"   🔍 Trying partial matches for 'No'...")
                                                    partial_options = page.locator('[role="option"]').all()
                                                    for option in partial_options:
                                                        if option.is_visible():
                                                            option_text = option.inner_text().lower().strip()
                                                            if option_text == "no" or option_text.endswith("no"):
                                                                option.click()
                                                                print(f"   ✅ MILITARY REGEX SUCCESS: Selected '{option_text}'")
                                                                time.sleep(1)
                                                                return True
                                                    
                                                    print(f"   ❌ Could not find 'No' option")
                                                    page.keyboard.press('Escape')
                                                    
                                                else:
                                                    print(f"   ✅ Military dropdown already filled: '{dropdown_text}'")
                                                    return True
                                                        
                                            except Exception as e:
                                                print(f"   ❌ Error with military dropdown: {e}")
                                                try:
                                                    page.keyboard.press('Escape')
                                                except:
                                                    pass
                                
                                # If we found a dropdown in this container, stop looking in other containers
                                container_dropdowns = container.locator('[role="combobox"], select, [aria-haspopup="listbox"], button[aria-expanded], button[aria-haspopup="listbox"]')
                                if container_dropdowns.count() > 0:
                                    print(f"   🛑 Found dropdown(s) in this container - stopping search here")
                                    break
                                
                except Exception as e:
                    continue
            
            print(f"   ❌ MILITARY REGEX HANDLER: Could not find military question")
            return False

        # Fill each question using pattern matching
        questions_filled = 0
        for pattern, answer in question_mappings.items():
            if fill_question_by_pattern(pattern, answer):
                questions_filled += 1
                # Scroll down after each successful question to bring next questions into view
                print(f"   📜 Scrolling down to reveal next questions...")
                page.evaluate("window.scrollBy(0, 300);")  # Scroll down 300px
                time.sleep(1)  # Brief pause to let scroll complete
            time.sleep(1)  # Brief pause between questions

        print(f"\n📊 Summary: Successfully filled {questions_filled}/{len(question_mappings)} questions")
        
        # SPECIAL MILITARY QUESTION HANDLER
        print(f"\n🪖 Running specialized military question handler...")
        military_filled = handle_military_question()
        if military_filled:
            questions_filled += 1
        
        # NOW CHECK FOR ANY REMAINING EMPTY DROPDOWNS
        print("\n🔍 Scanning for any remaining empty dropdowns...")
        
        # Find all dropdown elements on the page
        all_dropdown_selectors = [
            '[role="combobox"]',
            'select', 
            '[aria-haspopup="listbox"]',
            'button[aria-expanded]',
            'button[aria-haspopup="listbox"]',
            'button:has-text("Select One")',
            'button:has-text("Choose")',
            'button:has-text("Please select")',
        ]
        
        empty_dropdowns_found = 0
        for selector in all_dropdown_selectors:
            dropdowns = page.locator(selector)
            for i in range(dropdowns.count()):
                dropdown = dropdowns.nth(i)
                if dropdown.is_visible():
                    try:
                        if not is_dropdown_filled(dropdown):
                            empty_dropdowns_found += 1
                            dropdown_text = dropdown.inner_text()[:100]
                            
                            # Try to find the associated question text
                            question_text = "Unknown question"
                            try:
                                # Look for nearby label or fieldset with more comprehensive search
                                for level in range(1, 6):  # Check more ancestor levels
                                    container = dropdown.locator(f'xpath=ancestor::*[{level}]')
                                    
                                    # Try multiple ways to find question text
                                    question_selectors = [
                                        'label', 'legend', 'span', 'div', 'p', 
                                        '[data-automation-id*="question"]',
                                        'fieldset'
                                    ]
                                    
                                    for q_selector in question_selectors:
                                        try:
                                            question_elements = container.locator(q_selector)
                                            for j in range(min(3, question_elements.count())):
                                                elem_text = question_elements.nth(j).inner_text().strip()
                                                if (len(elem_text) > 20 and 
                                                    '?' in elem_text and 
                                                    not any(skip in elem_text.lower() for skip in 
                                                           ['skip to main', 'settings', 'english', 'candidate home'])):
                                                    question_text = elem_text[:200]
                                                    break
                                            if question_text != "Unknown question":
                                                break
                                        except:
                                            continue
                                    if question_text != "Unknown question":
                                        break
                            except:
                                pass
                            
                            print(f"\n🔴 EMPTY DROPDOWN FOUND #{empty_dropdowns_found}:")
                            print(f"   📍 Question: {question_text}")
                            print(f"   🎯 Dropdown text: '{dropdown_text}'")
                            print(f"   🔗 Selector: {selector}")
                            
                    except Exception as e:
                        print(f"   Error checking dropdown: {e}")
        
        if empty_dropdowns_found == 0:
            print("✅ No empty dropdowns found - all questions appear to be filled!")
        else:
            print(f"\n⚠️  Found {empty_dropdowns_found} empty dropdown(s) that need attention")
            
            # AUTO-FILL FALLBACK: Check empty dropdowns for question patterns and fill with "No"
            print(f"\n🔧 AUTO-FILL: Checking empty dropdowns for question patterns...")
            
            # Question patterns to look for - focused on military questions only
            military_patterns = [
                'uniformed services', 'active duty', 'guard', 'reserve', 
                'military', 'hiring program', 'service members'
            ]
            
            filled_count = 0
            for selector in all_dropdown_selectors:
                dropdowns = page.locator(selector)
                for i in range(dropdowns.count()):
                    dropdown = dropdowns.nth(i)
                    if dropdown.is_visible():
                        try:
                            if not is_dropdown_filled(dropdown):
                                dropdown_text = dropdown.inner_text()[:50]
                                print(f"   🔍 Found empty dropdown: '{dropdown_text}'")
                                
                                # Look for question text near this empty dropdown
                                question_found = False
                                for level in range(1, 5):
                                    container = dropdown.locator(f'xpath=ancestor::*[{level}]')
                                    container_text = ""
                                    try:
                                        container_text = container.inner_text().lower()
                                    except:
                                        continue
                                    
                                    # Check if any military pattern matches
                                    for pattern in military_patterns:
                                        if pattern in container_text:
                                            print(f"   ✅ Found question pattern: '{pattern}'")
                                            question_found = True
                                            break
                                    
                                    if question_found:
                                        break
                                
                                # If question pattern found, fill with "No"
                                if question_found:
                                    try:
                                        print(f"   🎯 Filling dropdown with 'No' based on pattern match...")
                                        dropdown.scroll_into_view_if_needed()
                                        dropdown.click()
                                        time.sleep(2)
                                        
                                        # Look for "No" option
                                        option = page.locator('[role="option"]:has-text("No")').first
                                        if option.count() > 0 and option.is_visible():
                                            option.click()
                                            print(f"   ✅ PATTERN-FILL SUCCESS: Selected 'No'")
                                            filled_count += 1
                                            time.sleep(1)
                                        else:
                                            print(f"   ❌ Could not find 'No' option")
                                            page.keyboard.press('Escape')
                                            
                                    except Exception as e:
                                        print(f"   ❌ Error filling dropdown: {e}")
                                        try:
                                            page.keyboard.press('Escape')
                                        except:
                                            pass
                                else:
                                    print(f"   ⚪ No question pattern found - skipping dropdown")
                                        
                        except Exception as e:
                            continue
            
            if filled_count > 0:
                print(f"🎉 AUTO-FILL COMPLETE: Filled {filled_count} additional dropdown(s)")
                questions_filled += filled_count
            else:
                print(f"❌ AUTO-FILL: Could not fill any remaining dropdowns")
        
    else:
        print("❌ Application Questions page not found")
    
    # Click Save and Continue at the end
    print("\n   Clicking Save and Continue...")
    time.sleep(2)
    save_button = page.locator('button:has-text("Save and Continue")').first
    if save_button.count() > 0:
        save_button.click()
        wait_for_page_load(page)
        debug_screenshot(page, "step_7_after_save")
        print("✅ STEP 7 COMPLETED: Application Questions page completed")
    else:
        print("❌ Save and Continue button not found")


# --------------------------------------------------
# STEP 8: Handle Voluntary Disclosures Page (4th Application Page)
# --------------------------------------------------
def step_8_voluntary_disclosures(page):
    """
    Step 8: Fill voluntary disclosure information
    """
    print("\n🔹 STEP 8: Handling Voluntary Disclosures page...")
    
    debug_screenshot(page, "step_8_voluntary_disclosures")
    
    # Look for dropdown elements
    dropdown_selectors = [
        '[role="combobox"]',
        'select',
        '[aria-haspopup="listbox"]',
        'button[aria-expanded]',
    ]
    
    all_dropdowns = []
    for selector in dropdown_selectors:
        elements = page.locator(selector)
        for i in range(elements.count()):
            element = elements.nth(i)
            if element.is_visible() and element.is_enabled():
                all_dropdowns.append(element)
    
    print(f"   Found {len(all_dropdowns)} dropdown elements")
    
    # Fill the voluntary disclosure dropdowns
    max_voluntary = min(2, len(all_dropdowns), len(VOLUNTARY_DISCLOSURE_ANSWERS))
    
    for i in range(max_voluntary):
        dropdown = all_dropdowns[i]
        answer = VOLUNTARY_DISCLOSURE_ANSWERS[i]
        
        print(f"   Filling voluntary dropdown {i+1}: '{answer}'")
        
        try:
            dropdown.scroll_into_view_if_needed()
            dropdown.click()
            time.sleep(1)
            
            # Look for answer option
            option = page.locator(f'[role="option"]:has-text("{answer}")').first
            if option.count() == 0:
                # Try partial match for longer answers
                words = answer.split()
                if len(words) > 1:
                    option = page.locator(f'[role="option"]:has-text("{words[0]}")').first
            
            if option.count() > 0:
                option.click()
                print(f"     ✅ Successfully selected: {answer}")
                time.sleep(0.5)
            else:
                print(f"     ❌ Could not find option: {answer}")
                dropdown.press('Escape')
                
        except Exception as e:
            print(f"     ❌ Error with voluntary dropdown {i+1}: {e}")
    
    # Look for and click checkbox
    print("   Looking for checkbox...")
    checkbox = page.locator('input[type="checkbox"]').first
    if checkbox.count() > 0 and checkbox.is_visible():
        print("   Clicking checkbox...")
        checkbox.click()
        time.sleep(1)
    
    # Click Save and Continue
    print("   Clicking Save and Continue...")
    time.sleep(2)
    save_button = page.locator('button:has-text("Save and Continue")').first
    save_button.click()
    
    wait_for_page_load(page)
    debug_screenshot(page, "step_8_after_save")
    print("✅ STEP 8 COMPLETED: Voluntary Disclosures page completed")


# --------------------------------------------------
# STEP 9: Handle Review and Submit Page (5th Application Page)
# --------------------------------------------------
def step_9_review_and_submit(page):
    """
    Step 9: Review and submit the application
    """
    print("\n🔹 STEP 9: Handling Review and Submit page...")
    
    debug_screenshot(page, "step_9_review_page")
    
    # Wait before submitting
    print("   Waiting 5 seconds before submission...")
    time.sleep(5)
    
    # Look for Submit button
    submit_selectors = [
        'button:has-text("Submit")',
        'button:has-text("Submit Application")',
        'input[type="submit"]',
        'button[type="submit"]',
    ]
    
    submit_clicked = False
    for selector in submit_selectors:
        submit_button = page.locator(selector).first
        if submit_button.count() > 0 and submit_button.is_visible():
            print(f"   Found Submit button: {selector}")
            submit_button.click()
            submit_clicked = True
            break
    
    if submit_clicked:
        print("🎉 APPLICATION SUBMITTED SUCCESSFULLY! 🎉")
        wait_for_page_load(page)
        debug_screenshot(page, "step_9_submitted")
    else:
        print("⚠ Could not find Submit button")
        debug_screenshot(page, "step_9_no_submit")
    
    print("✅ STEP 9 COMPLETED: Application submission attempted")
    return submit_clicked


# --------------------------------------------------
# Main Application Flow
# --------------------------------------------------
def apply_to_job(job_id: str):
    """
    Complete application flow for a single job
    """
    print(f"\n{'='*60}")
    print(f"🚀 STARTING APPLICATION FOR JOB: {job_id}")
    print(f"{'='*60}")
    
    submission_successful = False
    application_completed = False
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()
        
        try:
            # Execute each step in sequence
            step_1_login(page)
            step_2_navigate_to_jobs(page)
            step_3_search_job(page, job_id)
            step_4_click_apply(page, job_id)
            step_5_my_information(page)
            step_6_my_experience(page)
            step_7_application_questions(page)
            step_8_voluntary_disclosures(page)
            
            # Track if submission was successful
            submission_successful = step_9_review_and_submit(page)
            application_completed = True
            
            if submission_successful:
                print(f"\n🎉 COMPLETED APPLICATION FLOW FOR JOB: {job_id}")
                SUCCESSFUL_SUBMISSIONS.append(job_id)
            else:
                print(f"\n⚠️  APPLICATION COMPLETED BUT SUBMISSION FAILED FOR JOB: {job_id}")
                INCOMPLETE_SUBMISSIONS.append(job_id)
            
        except Exception as e:
            print(f"\n❌ ERROR during application for {job_id}: {e}")
            debug_screenshot(page, f"error_{job_id}")
            FAILED_SUBMISSIONS.append(job_id)
            
        finally:
            print(f"\n⏳ Waiting 3 seconds before closing browser...")
            time.sleep(3)
            browser.close()


def save_job_tracking_results():
    """
    Save job application results to job_result.txt file for tracking
    """
    result_file = Path("job_result.txt")
    
    with open(result_file, "w") as f:
        f.write("# WALMART JOB APPLICATION RESULTS\n")
        f.write(f"# Generated on: {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        
        # Write summary
        f.write("# SUMMARY:\n")
        f.write(f"# Total jobs processed: {len(JOB_IDS)}\n")
        f.write(f"# Successful submissions: {len(SUCCESSFUL_SUBMISSIONS)}\n")
        f.write(f"# Incomplete submissions: {len(INCOMPLETE_SUBMISSIONS)}\n")
        f.write(f"# Failed applications: {len(FAILED_SUBMISSIONS)}\n\n")
        
        # Write successful submissions
        if SUCCESSFUL_SUBMISSIONS:
            f.write("# ✅ SUCCESSFUL SUBMISSIONS (COMPLETED):\n")
            for job_id in SUCCESSFUL_SUBMISSIONS:
                f.write(f"{job_id}\n")
            f.write("\n")
        
        # Write failed submissions that need manual completion
        if FAILED_SUBMISSIONS:
            f.write("# ❌ FAILED APPLICATIONS (NEED MANUAL COMPLETION):\n")
            f.write("# Copy these to .env JOB_IDS for retry:\n")
            failed_ids = ", ".join(FAILED_SUBMISSIONS)
            f.write(f"JOB_IDS={failed_ids}\n\n")
            f.write("# Individual failed job IDs:\n")
            for job_id in FAILED_SUBMISSIONS:
                f.write(f"{job_id}\n")
            f.write("\n")
        
        # Write incomplete submissions that need manual review
        if INCOMPLETE_SUBMISSIONS:
            f.write("# ⚠️ INCOMPLETE SUBMISSIONS (NEED MANUAL REVIEW/SUBMIT):\n")
            f.write("# Applications completed but submission failed - check manually:\n")
            incomplete_ids = ", ".join(INCOMPLETE_SUBMISSIONS)
            f.write(f"INCOMPLETE_IDS={incomplete_ids}\n\n")
            f.write("# Individual incomplete job IDs:\n")
            for job_id in INCOMPLETE_SUBMISSIONS:
                f.write(f"{job_id}\n")
            f.write("\n")
        
        # Instructions for next run
        if FAILED_SUBMISSIONS or INCOMPLETE_SUBMISSIONS:
            f.write("# 📝 NEXT STEPS:\n")
            f.write("# 1. For FAILED jobs: Copy the JOB_IDS line above to your .env file\n")
            f.write("# 2. For INCOMPLETE jobs: Manually visit and submit these applications\n")
            f.write("# 3. Remove successfully completed jobs from your .env file\n")
    
    print(f"📝 Job results saved to: {result_file}")
    
    # Also save to logs directory for backup
    backup_file = LOG_DIR / f"job_result_backup_{time.strftime('%Y%m%d_%H%M%S')}.txt"
    import shutil
    shutil.copy2(result_file, backup_file)
    print(f"📝 Backup saved to: {backup_file}")
    
    return result_file


def main():
    """
    Main function to process all job applications
    """
    if not WORKDAY_URL or not USERNAME or not PASSWORD:
        print("❌ WORKDAY_URL, WORKDAY_USER, or WORKDAY_PASS not set in .env")
        return

    if not JOB_IDS:
        print("❌ No JOB_IDS provided in .env")
        return

    print("🎯 Starting Walmart Workday Automation")
    print(f"📋 Job IDs to process: {JOB_IDS}")
    
    for job_id in JOB_IDS:
        apply_to_job(job_id)
        
        # Wait between applications
        if len(JOB_IDS) > 1:
            print(f"\n⏳ Waiting 10 seconds before next application...")
            time.sleep(10)
    
    print(f"\n✅ ALL APPLICATIONS PROCESSED!")
    
    # Print summary
    print(f"\n📊 FINAL SUMMARY:")
    print(f"✅ Successful submissions: {len(SUCCESSFUL_SUBMISSIONS)}")
    print(f"⚠️  Incomplete submissions: {len(INCOMPLETE_SUBMISSIONS)}")
    print(f"❌ Failed applications: {len(FAILED_SUBMISSIONS)}")
    
    if FAILED_SUBMISSIONS:
        print(f"\n❌ FAILED JOB IDS (need manual completion):")
        for job_id in FAILED_SUBMISSIONS:
            print(f"   - {job_id}")
    
    if INCOMPLETE_SUBMISSIONS:
        print(f"\n⚠️  INCOMPLETE JOB IDS (completed but not submitted):")
        for job_id in INCOMPLETE_SUBMISSIONS:
            print(f"   - {job_id}")
    
    # Save results to job_result.txt file
    result_file = save_job_tracking_results()
    
    if FAILED_SUBMISSIONS or INCOMPLETE_SUBMISSIONS:
        print(f"\n📝 Check {result_file} for:")
        print(f"   - Failed job IDs to copy to .env for retry")
        print(f"   - Incomplete job IDs for manual completion")
        print(f"   - Ready-to-copy JOB_IDS line for .env file")


if __name__ == "__main__":
    main()