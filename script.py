import requests
import re

kaggle_org_repo_url = "https://api.github.com/orgs/Kaggle/repos"
kaggle_org_repos = requests.get(kaggle_org_repo_url)
kaggle_org_repos_dict = kaggle_org_repos.json()

def get_number_commits(owner, repo):
    commits = requests.get(f'https://api.github.com/repos/{owner}/{repo}/commits?per_page=1')
    # print(commits.headers)
    # print(commits)
    if 'Link' in commits.headers:
        return re.search(r'page=(\d+)>; rel="last"', commits.headers['Link']).group(1)
    
    return len(commits.json())

for repo in kaggle_org_repos_dict:
    print(repo['name'])
    print(get_number_commits('Kaggle', repo['name']))


# print(get_number_commits('Kaggle', 'kagglehub'))