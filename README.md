# Project Overview

This project contains scripts that interact with external APIs for data extraction and processing. In particular, it includes:

- **Kaggle Script:** Located in the `Kaggle/` directory, this script interacts with the GitHub API. It is recommended to use an authentication token to avoid strict rate limits imposed on unauthorized requests.
- **Jira Crawler:** A Python-based crawler that retrieves issue data from the Jira REST API (for example, for issue `CAMEL-10597`). The crawler extracts key details such as:
  - **Details:** Issue type (e.g. _Bug_)
  - **People:** Assignee (e.g. _Claus Ibsen_)
  - **Dates:** Created date in both ISO format and as an epoch timestamp
  - **Description:** Issue description (with all newlines removed so that the CSV format remains intact)
  - **Comments:** All comments formatted on one line (e.g. _Author:epoch:human date: comment text_)

## Requirements

- Python 3.x
- [requests](https://docs.python-requests.org/)
- Standard libraries: `csv`, `json`, `datetime`, and `re` (for cleaning up whitespace)

## Setup

### Authentication Token for Kaggle Script

To run the Kaggle script, you must have a `token.env` file inside the `Kaggle/` directory. This file should include your API token to authenticate your GitHub API requests, which helps you avoid the stricter rate limits for unauthenticated requests.

Example content for `token.env`: GITHUB_TOKEN=your_token_here

Even though the code will run without the token, using it is more robust and will prevent unexpected API rate limiting.
