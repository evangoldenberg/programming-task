import re
import time
import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options
from bs4 import BeautifulSoup

# Import Selenium helpers for waiting and element lookup
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


# cleans up text by replacing lots of whitespace with a single space
def clean_text(text):
    return re.sub(r'\s+', ' ', text).strip()


# takes the BeautifulSoup object and returns a dict of issue details
def extract_details(soup):
    data = {}
    # Basic details using their IDs
    fields = {
        'Type': '#type-val',
        'Status': '#status-val',
        'Priority': '#priority-val',
        'Resolution': '#resolution-val',
        'Affects Version/s': '#versions-val',
        'Fix Version/s': '#fixfor-val',
        'Component/s': '#components-val',
        'Labels': '#labels-13028113-value'
    }
    for key, selector in fields.items():
        element = soup.select_one(selector)
        if element:
            data[key] = element.get_text(strip=True)
    
    # Custom fields by their IDs
    custom_fields = {
        'Patch Info': '#customfield_12310041-val',
        'Estimated Complexity': '#customfield_12310060-val'
    }
    for key, selector in custom_fields.items():
        element = soup.select_one(selector)
        if element:
            data[key] = element.get_text(strip=True)
    
    return data


# takes the BeautifulSoup object and returns a dict of people data
def extract_people_data(soup):
    people_data = {}
    people_section = soup.find("div", class_="item-details people-details")
    if people_section:
        assignee_elem = people_section.find("span", id="assignee-val")
        if assignee_elem:
            people_data["Assignee"] = assignee_elem.get_text(strip=True)
        
        reporter_elem = people_section.find("span", id="reporter-val")
        if reporter_elem:
            people_data["Reporter"] = reporter_elem.get_text(strip=True)
    
    return people_data


# takes the BeautifulSoup object and returns a dict of date data
def extract_date_data(soup):
    date_data = {}
    date_fields = {
        "Created": "created-val",
        "Updated": "updated-val",
        "Resolved": "resolutiondate-val"
    }
    
    for key, span_id in date_fields.items():
        span = soup.find("span", id=span_id)
        if span:
            time_elem = span.find("time")
            if time_elem:
                date_data[key] = time_elem.get_text(strip=True)
    
    return date_data


# takes the BeautifulSoup object and returns the description text of the issue
def extract_description_data(soup):
    description_div = soup.find("div", id="description-val")
    if description_div:
        description_text = description_div.get_text(separator="\n", strip=True)
        return clean_text(description_text)
    return ""


# takes the BeautifulSoup object and returns a list of comments (as dicts) from the page
def extract_comments(soup):
    comments = []
    container = soup.find("div", id="issue_actions_container")
    if container is None:
        return comments

    comment_divs = container.find_all("div", id=re.compile(r"^comment-\d+"))
    
    for div in comment_divs:
        # Find the 'concise' div without using lambda functions
        concise = None
        for child in div.find_all("div"):
            class_list = child.get("class")
            if class_list is not None and "concise" in class_list:
                concise = child
                break
        if concise is None:
            continue
        
        # Now find the 'action-details' div inside the concise div
        details = None
        for child in concise.find_all("div"):
            class_list = child.get("class")
            if class_list is not None and "action-details" in class_list:
                details = child
                break
        if details is None:
            continue
        
        # Look for the anchor tag with 'user-hover' class to get the commenter
        commenter_anchor = None
        for a in details.find_all("a"):
            class_list = a.get("class")
            if class_list is not None and "user-hover" in class_list:
                commenter_anchor = a
                break
        if commenter_anchor is not None:
            commenter = commenter_anchor.get_text(strip=True)
        else:
            commenter = "Unknown"
            
        comment_text = details.get_text(separator=" ", strip=True)
        
        comments.append({
            "commenter": clean_text(commenter),
            "comment": clean_text(comment_text)
        })
    
    return comments


# takes the URL of the issue and the selenium webdriver instance
# uses Selenium to load the issue page, then passes it to our scraping functions
def process_issue(url, driver):
    driver.get(url)
    driver.implicitly_wait(10)
    time.sleep(2)  # slow down a bit to see the page
    html = driver.page_source
    soup = BeautifulSoup(html, "html.parser")
    
    # Get all the extracted data
    issue_data = {"URL": url}
    issue_data.update(extract_details(soup))
    issue_data.update(extract_people_data(soup))
    issue_data.update(extract_date_data(soup))
    issue_data["Description"] = extract_description_data(soup)
    
    # Flatten comments into a single string
    comments = extract_comments(soup)
    if comments:
        formatted_comments = " | ".join([f"{c['commenter']}: {c['comment']}" for c in comments])
    else:
        formatted_comments = ""
    issue_data["Comments"] = formatted_comments
    
    return issue_data


# writes a list of issue dicts to a CSV file using Pandas
def write_to_csv(data, filename):
    df = pd.DataFrame(data)
    df.to_csv(filename, index=False)
    print(f"Data written to {filename}")


# crawls the issue list page by clicking the "Next" button until no more pages are available.
def crawl_issue_list(driver, start_url):
    issue_urls = []
    driver.get(start_url)
    time.sleep(2)  # wait for the page to load
    
    while True:
        html = driver.page_source
        soup = BeautifulSoup(html, "html.parser")
        
        # Scrape all issues in the <ol class="issue-list">
        issue_list = soup.find("ol", class_="issue-list")
        if issue_list:
            li_items = issue_list.find_all("li")
            for li in li_items:
                a_tag = li.find("a", class_="splitview-issue-link")
                if a_tag:
                    href = a_tag.get("href")
                    if href.startswith("/"):
                        href = "https://issues.apache.org" + href
                    if href not in issue_urls:
                        issue_urls.append(href)
        
        # Try to click the "Next" button
        try:
            # Wait for the next button to be clickable
            next_button = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "a.nav-next"))
            )
            print("Clicking Next button...")
            next_button.click()
            time.sleep(2)  # wait for new page to load
        except Exception as e:
            print("No more pages or error clicking next:", e)
            break
    
    return issue_urls


# main function to crawl all active issues, process each issue, and export to CSV
def main(start_url, output_csv="issues_data.csv"):
    chrome_options = Options()
    chrome_options.add_argument("--headless=new")
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
    
    print(f"Starting crawl at: {start_url}")
    issue_urls = crawl_issue_list(driver, start_url)
    print(f"Found {len(issue_urls)} issues")
    
    all_issues_data = []
    for url in issue_urls:
        print(f"Processing issue: {url}")
        issue_data = process_issue(url, driver)
        all_issues_data.append(issue_data)
    
    driver.quit()
    write_to_csv(all_issues_data, output_csv)


if __name__ == '__main__':
    # Starting URL for active CAMEL issues
    start_url = "https://issues.apache.org/jira/projects/CAMEL/issues"
    main(start_url, output_csv="issues_data.csv")
