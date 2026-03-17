import os
import time
import random
import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By
from tqdm import tqdm

# Config
MY_UID = "7208849414"  # Your Weibo UID
TEMP_PROFILE = r"C:\Users\24078\EdgeSeleniumProfile"  # Your Edge profile folder
SAVE_FOLDER = "weibo_friends_follow"
MY_FOLLOW_FILE = os.path.join(SAVE_FOLDER, "my_follow_list.csv")
ALL_FRIENDS_FILE = os.path.join(SAVE_FOLDER, "all_friends_follow.csv")

# Start Edge browser
def start_browser():
    options = webdriver.EdgeOptions()
    options.use_chromium = True
    options.add_argument("--start-maximized")
    options.add_argument(f"--user-data-dir={TEMP_PROFILE}")  # Keep login
    driver = webdriver.Edge(options=options)
    return driver

# Get follow list for a UID (small step scrolling)
def get_follow_list(driver, uid, max_idle=20):
    url = f"https://weibo.com/u/page/follow/{uid}"
    driver.get(url)
    print(f"Loading follow list for UID {uid}...")
    time.sleep(8)  # Wait initial render

    result = {}
    last_position = 0
    idle_time = 0

    while True:
        # Get currently visible users
        cards = driver.find_elements(By.CSS_SELECTOR, "span[usercard]")
        for card in cards:
            try:
                user_id = card.get_attribute("usercard")
                name = card.text.strip()
                if user_id and name:
                    result[user_id] = name
            except:
                continue

        # Scroll down a small step
        driver.execute_script("window.scrollBy(0, 600);")
        time.sleep(2 + random.random())  # Wait for loading

        # Check if page bottom reached
        current_position = driver.execute_script("return window.pageYOffset;")
        if current_position == last_position:
            idle_time += 2
        else:
            idle_time = 0

        if idle_time > max_idle:
            break

        last_position = current_position

    print(f"Fetched {len(result)} follows for UID {uid}")
    return result

# Main program
def main():
    if not os.path.exists(SAVE_FOLDER):
        os.makedirs(SAVE_FOLDER)

    driver = start_browser()
    input("Browser opened. Please login to Weibo, then press Enter to continue...")

    # Step 1: Load my follow list from file
    if os.path.exists(MY_FOLLOW_FILE):
        print(f"Loading my follow list from {MY_FOLLOW_FILE}...")
        df_my = pd.read_csv(MY_FOLLOW_FILE, encoding="utf-8-sig")
        my_friends = dict(zip(df_my["uid"], df_my["name"]))
    else:
        print("Fetching my follow list from Weibo...")
        my_friends = get_follow_list(driver, MY_UID)
        if my_friends:
            df_my = pd.DataFrame(list(my_friends.items()), columns=["uid", "name"])
            df_my.to_csv(MY_FOLLOW_FILE, index=False, encoding="utf-8-sig")
            print(f"My follow list saved to {MY_FOLLOW_FILE}")
        else:
            print("Failed to fetch my follow list. Check login or page load.")
            driver.quit()
            return

    # Step 2: Fetch friends' follow lists
    all_friends_follow = []
    for uid, name in tqdm(my_friends.items(), desc="Fetching friends' follows"):
        file_name = os.path.join(SAVE_FOLDER, f"{name}_{uid}.csv")
        if os.path.exists(file_name):
            print(f"File {file_name} already exists. Skipping {name}...")
            df_existing = pd.read_csv(file_name, encoding="utf-8-sig")
            all_friends_follow.extend(df_existing.values.tolist())
            continue

        try:
            follow_data = get_follow_list(driver, uid)
            rows = [[uid, name, fid, fname] for fid, fname in follow_data.items()]
            all_friends_follow.extend(rows)

            df = pd.DataFrame(rows, columns=["friend_uid", "friend_name", "follow_uid", "follow_name"])
            df.to_csv(file_name, index=False, encoding="utf-8-sig")
            time.sleep(random.uniform(3, 6))
        except Exception as e:
            print(f"Failed fetching {name}'s follows: {e}")

    # Step 3: Save aggregated file
    if all_friends_follow:
        df_all = pd.DataFrame(all_friends_follow, columns=["friend_uid", "friend_name", "follow_uid", "follow_name"])
        df_all.to_csv(ALL_FRIENDS_FILE, index=False, encoding="utf-8-sig")
        print(f"All friends' follow lists aggregated to {ALL_FRIENDS_FILE}")

    driver.quit()
    print("Done! All data saved in folder:", SAVE_FOLDER)

if __name__ == "__main__":
    main()