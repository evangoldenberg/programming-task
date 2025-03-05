import requests
import csv
import re
from datetime import datetime

def safe_get(d, *keys, default="N/A"):
    """
    Traverse a nested dictionary using the provided keys.
    If any key is missing or the value is None, returns default.
    """
    for key in keys:
        if isinstance(d, dict):
            d = d.get(key)
        else:
            return default
    return d if d is not None else default

def iso_to_epoch(iso_str):
    """
    Converts an ISO 8601 date string (with milliseconds and timezone)
    into an epoch timestamp and a human-readable string.
    """
    dt = datetime.strptime(iso_str, "%Y-%m-%dT%H:%M:%S.%f%z")
    epoch = int(dt.timestamp())
    human_readable = dt.strftime("%d/%b/%y %H:%M")
    return epoch, human_readable

def fetch_issue(issue_key):
    """
    Makes a GET request to the Jira REST API to retrieve issue data.
    """
    url = f"https://issues.apache.org/jira/rest/api/2/issue/{issue_key}"
    # Specify the fields we need.
    params = {
        "fields": "key,summary,description,created,assignee,issuetype,comment"
    }
    response = requests.get(url, params=params)
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Error fetching issue {issue_key}: {response.status_code}")
        return None

def extract_issue_data(issue):
    """
    Extracts the desired fields from the issue JSON:
      - Type (from issue type)
      - Assignee (display name)
      - Created (human-readable and epoch)
      - Description
      - Comments (concatenated into one string)
    """
    fields = issue.get("fields", {})

    # Details: Issue type (e.g., Bug)
    issue_type = safe_get(fields, "issuetype", "name")

    # People: Assignee display name
    assignee = safe_get(fields, "assignee", "displayName")

    # Dates: Created date in ISO format -> convert to epoch and human-readable
    created_iso = safe_get(fields, "created", default="")
    if created_iso != "N/A" and created_iso:
        created_epoch, created_human = iso_to_epoch(created_iso)
    else:
        created_epoch, created_human = "N/A", "N/A"

    # Description - remove newline characters and extra spaces
    description = safe_get(fields, "description", default="N/A")
    description = re.sub(r'\s+', ' ', description).strip()


    # Comments: Process each comment
    comments_data = safe_get(fields, "comment", "comments", default=[])
    comment_list = []
    for comment in comments_data:
        author = safe_get(comment, "author", "displayName")
        comment_created_iso = safe_get(comment, "created", default="")
        if comment_created_iso != "N/A" and comment_created_iso:
            comment_epoch, comment_human = iso_to_epoch(comment_created_iso)
        else:
            comment_epoch, comment_human = "N/A", "N/A"
        body = safe_get(comment, "body", default="N/A").replace("\n", " ").strip()
        # Format each comment as "Author:epoch:human_date: comment text"
        comment_str = f"{author}:{comment_epoch}:{comment_human}: {body}"
        comment_list.append(comment_str)
    comments_combined = " | ".join(comment_list) if comment_list else "N/A"

    return {
        "Type": issue_type,
        "Assignee": assignee,
        "Created": created_human,
        "Created Epoch": created_epoch,
        "Description": description,
        "Comments": comments_combined
    }


def save_issues_to_csv(issues, filename):
    """
    Writes a list of extracted issue data dictionaries to a CSV file.
    """
    fieldnames = ["Type", "Assignee", "Created", "Created Epoch", "Description", "Comments"]
    with open(filename, "w", newline="", encoding="utf-8") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        for issue in issues:
            data = extract_issue_data(issue)
            writer.writerow(data)
    print(f"Saved {len(issues)} issues to {filename}")

def main():
    # List of issue keys to process – you can add as many as needed.
    issue_keys = ["CAMEL-10597", "CAMEL-21831", "CAMEL-21830", "CAMEL-20367" ]  # e.g., add more keys like "CAMEL-10596", "CAMEL-10595", etc.
    
    issues = []
    for key in issue_keys:
        data = fetch_issue(key)
        if data:
            issues.append(data)
    
    if issues:
        save_issues_to_csv(issues, "jira_issues.csv")
    else:
        print("No issues were fetched.")

if __name__ == "__main__":
    main()
