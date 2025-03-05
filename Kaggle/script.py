import requests
import json
import re
import os
from datetime import datetime
from dotenv import load_dotenv

# Load GitHub token from token.env file
load_dotenv('token.env')
my_token = os.getenv("GITHUB_TOKEN")

auth_header = {
    "Authorization": f"token {my_token}",
    "Accept": "application/vnd.github+json"
}

# Retrieve Kaggle organization repositories
kaggle_org_repo_url = "https://api.github.com/orgs/Kaggle/repos"
response = requests.get(kaggle_org_repo_url, headers=auth_header)
try:
    kaggle_org_repos = response.json()
except ValueError:
    kaggle_org_repos = []

def get_paged_info(owner, repo, endpoints=['commits', 'contributors', 'branches', 'tags', 'releases']):
    """
    Retrieve counts for various repository endpoints using pagination.
    
    Parameters:
        owner (str): Repository owner.
        repo (str): Repository name.
        endpoints (list): List of endpoints to query.
        
    Returns:
        list of tuples: Each tuple contains (endpoint, count).
    """
    counts = []
    for endpoint in endpoints:
        url = f'https://api.github.com/repos/{owner}/{repo}/{endpoint}?per_page=1'
        response = requests.get(url, headers=auth_header)
        
        if response.status_code == 204:
            counts.append((endpoint, 0))
        else:
            try:
                data = response.json()
            except ValueError:
                data = None

            if data is None:
                counts.append((endpoint, 0))
            elif 'Link' in response.headers:
                # Extract last page number from Link header if paginated
                match = re.search(r'page=(\d+)>; rel="last"', response.headers['Link'])
                counts.append((endpoint, int(match.group(1))) if match else (endpoint, len(data)))
            else:
                counts.append((endpoint, len(data)) if isinstance(data, list) else (endpoint, 0))
    return counts

def get_closed_issues_count(owner, repo, token=None):
    """
    Retrieve the count of closed issues using the search endpoint.
    
    Parameters:
        owner (str): Repository owner.
        repo (str): Repository name.
        token (str): Optional GitHub token.
        
    Returns:
        int: Count of closed issues.
    """
    url = "https://api.github.com/search/issues"
    headers = {"Accept": "application/vnd.github+json"}
    if token:
        headers["Authorization"] = f"token {token}"
    query = f"repo:{owner}/{repo} is:issue is:closed"
    params = {"q": query}
    response = requests.get(url, headers=headers, params=params)
    try:
        data = response.json()
    except ValueError:
        data = {}
    return data.get("total_count", 0)

def get_repo_languages(owner, repo):
    """
    Retrieve the languages used in a repository along with their byte counts.
    
    Parameters:
        owner (str): Repository owner.
        repo (str): Repository name.
        
    Returns:
        list of tuples: Each tuple contains (language, byte_count).
    """
    url = f"https://api.github.com/repos/{owner}/{repo}/languages"
    response = requests.get(url)
    if response.status_code != 200:
        raise Exception(f"Error fetching languages: {response.status_code}")
    return list(response.json().items())

def get_repo_info(owner, repo):
    """
    Retrieve repository metrics including paged info, stars, forks,
    closed issues, and environments.
    
    Parameters:
        owner (str): Repository owner.
        repo (str): Repository name.
        
    Returns:
        list of tuples: Each tuple contains a metric name and its value.
    """
    counts = get_paged_info(owner, repo)
    
    # Get repository details
    repo_url = f'https://api.github.com/repos/{owner}/{repo}'
    repo_response = requests.get(repo_url, headers=auth_header)
    try:
        repo_data = repo_response.json()
    except ValueError:
        repo_data = {}
    
    stars = repo_data.get('stargazers_count', 0)
    forks = repo_data.get('forks_count', 0)
    closed_issues = get_closed_issues_count(owner, repo)
    
    # Get environments count
    env_url = f'https://api.github.com/repos/{owner}/{repo}/environments'
    env_response = requests.get(env_url, headers=auth_header)
    try:
        env_data = env_response.json()
    except ValueError:
        env_data = {}
    environments = env_data.get('total_count', 0)
    
    counts.extend([
        ('stars', stars),
        ('forks', forks),
        ('environments', environments),
        ('closed issues', closed_issues)
    ])
    
    return counts

def save_data_to_json(data, filename_prefix="data"):
    """
    Save the provided data to a JSON file with a date-stamped filename.
    
    Parameters:
        data: Data to be saved (typically a dict or list).
        filename_prefix (str): Prefix for the filename.
    """
    date_str = datetime.now().strftime("%Y_%m_%d")
    filename = f"{filename_prefix}_{date_str}.json"
    with open(filename, "w") as f:
        json.dump(data, f, indent=4)
    print(f"Data saved to {filename}")

if __name__ == "__main__":
    all_repo_data = []
    for repo in kaggle_org_repos:
        repo_name = repo.get('name')
        repo_metrics = get_repo_info('Kaggle', repo_name)
        repo_languages = get_repo_languages('Kaggle', repo_name)
        repo_data = {
            "repository": repo_name,
            "metrics": repo_metrics,
            "languages": repo_languages
        }
        print(repo_data)
        all_repo_data.append(repo_data)
    
    save_data_to_json(all_repo_data, filename_prefix="kaggle_data")
