import os
import sys
import requests
from github import Github
from dotenv import load_dotenv
import logging

logging.basicConfig(
    level=logging.INFO,  # Change to DEBUG for more details
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("pr_review_bot.log"),  # Save logs to file
        logging.StreamHandler()  # Show logs in console
    ]
)



# Load tokens from .env
def load_tokens():
    load_dotenv()

    gh = os.getenv("GITHUB_TOKEN")
    or_key = os.getenv("OPENROUTER_API_KEY")

    if not gh:
        raise RuntimeError("GITHUB_TOKEN missing. Make sure it is set in .env or environment variables!")
    if not or_key:
        raise RuntimeError("OPENROUTER_API_KEY missing. Make sure it is set in .env or environment variables!")

    return gh, or_key


# Call AI model via OpenRouter API
def get_ai_suggestions(or_key, file_diffs):
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {or_key}",
        "Content-Type": "application/json"
    }

    prompt = f"""
You are a senior software engineer reviewing a pull request.

The PR changes are below:
{file_diffs}


Write a structured PR review with the following format:

📄 File: <file_name>
🔍 PR Review Summary

1. 📖 Documentation
   - [Suggestion] ...

2. ✅ Style & Readability
   - [Optional] ...

3. 🧪 Testing
   - [Critical] ...

4. 🔒 Error Handling
   - [Suggestion] ...

5. 🚀 Scalability & Future Considerations
   - [Optional] ...

---

📊 PR Metrics:
- Files changed
- Functions modified
- Lines changed

✅ Final Verdict: Approved / Needs minor improvements / Needs major changes
"""


    payload = {
        "model": "openai/gpt-4o-mini",  # you can change model if needed
        "messages": [
            {"role": "system", "content": "You are a senior code reviewer."},
            {"role": "user", "content": prompt}
        ]
    }

    response = requests.post(url, headers=headers, json=payload)

    if response.status_code != 200:
        raise RuntimeError(f"AI API request failed: {response.text}")

    return response.json()["choices"][0]["message"]["content"]


def main():
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,  # Change to DEBUG for more details
        format="%(asctime)s - %(levelname)s - %(message)s",
        handlers=[
            logging.StreamHandler(),  # Console output
            logging.FileHandler("pr_review_bot.log", mode="a")  # Save logs to file
        ]
    )

    if len(sys.argv) != 3:
        logging.error("Usage: python pr_review_bot.py <repo_name> <pr_number>")
        sys.exit(1)

    repo_name = sys.argv[1]
    pr_number = int(sys.argv[2])

    try:
        # Load tokens
        gh_token, or_key = load_tokens()
        logging.info("Tokens loaded successfully. Bot is running...")

        # Connect to GitHub
        g = Github(gh_token)
        repo = g.get_repo(repo_name)
        pr = repo.get_pull(pr_number)
        logging.info(f"Connected to repo '{repo_name}', PR #{pr_number}")

        # Collect diffs
        file_diffs = ""
        logging.info(f"Changed files in PR #{pr_number}:")
        for f in pr.get_files():
            logging.info(f"   - {f.filename}")
            file_diffs += f"\n\nFile: {f.filename}\nPatch:\n{f.patch}"

        # Get AI review
        logging.info("Requesting AI suggestions...")
        ai_suggestions = get_ai_suggestions(or_key, file_diffs)
        logging.info("AI suggestions generated successfully.")

        # Post AI suggestions as PR comment
        pr.create_issue_comment(ai_suggestions)
        logging.info(f"AI suggestions posted to PR #{pr_number} successfully!")

    except Exception as e:
        logging.exception(f"An error occurred while processing PR #{pr_number}: {e}")


if __name__ == "__main__":
    main()
