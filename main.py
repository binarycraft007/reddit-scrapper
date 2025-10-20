import os
import json
import logging
import argparse
from datetime import datetime
from typing import Dict, List, Iterator

import praw
from dotenv import load_dotenv
from tqdm import tqdm

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)


def create_reddit_instance() -> praw.Reddit:
    """Creates and returns a Reddit instance after authenticating."""
    load_dotenv()

    required_vars = [
        "CLIENT_ID",
        "CLIENT_SECRET",
        "USER_AGENT",
        "REDDIT_USERNAME",
        "REDDIT_PASSWORD",
    ]
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    if missing_vars:
        raise ValueError(
            f"Missing required environment variables: {', '.join(missing_vars)}"
        )

    logging.info("Authenticating with Reddit API...")

    try:
        reddit = praw.Reddit(
            client_id=os.getenv("CLIENT_ID"),
            client_secret=os.getenv("CLIENT_SECRET"),
            user_agent=os.getenv("USER_AGENT"),
            username=os.getenv("REDDIT_USERNAME"),
            password=os.getenv("REDDIT_PASSWORD"),
        )
        # Check if login was successful
        reddit.user.me()
        logging.info("Authentication successful.")
        return reddit
    except Exception as e:
        logging.error(f"Failed to authenticate with Reddit: {e}")
        raise


def fetch_posts(
    reddit: praw.Reddit, query: str, subreddit_name: str, limit: int
) -> Iterator[Dict]:
    """Fetches posts from a subreddit based on a query and yields them."""
    try:
        subreddit = reddit.subreddit(subreddit_name)
        logging.info(
            f"Searching for '{query}' in r/{subreddit_name} (limit: {limit})..."
        )

        # Use tqdm for a progress bar
        search_results = subreddit.search(query=query, sort="new", limit=limit)
        for submission in tqdm(search_results, total=limit, desc="Fetching posts"):
            yield {
                "id": submission.id,
                "title": submission.title,
                "selftext": submission.selftext,
                "author": str(submission.author),
                "created_utc": submission.created_utc,
                "score": submission.score,
                "url": submission.url,
                "num_comments": submission.num_comments,
                "subreddit": str(submission.subreddit),
            }
    except Exception as e:
        logging.error(f"An error occurred while fetching posts: {e}")
        raise


def save_to_json(data: List[Dict], filename: str):
    """Saves a list of dictionaries to a JSON file."""
    logging.info(f"Saving {len(data)} posts to {filename}...")
    try:
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        logging.info("Successfully saved data.")
    except IOError as e:
        logging.error(f"Failed to write to file {filename}: {e}")
        raise


def main():
    """Main function to parse arguments and run the data collection."""
    parser = argparse.ArgumentParser(
        description="Collect Reddit posts based on a search query."
    )
    parser.add_argument("query", type=str, help="The search query for Reddit.")
    parser.add_argument(
        "--subreddit",
        "-s",
        type=str,
        default="all",
        help="The subreddit to search in (default: 'all').",
    )
    parser.add_argument(
        "--limit",
        "-l",
        type=int,
        default=100,
        help="The maximum number of posts to fetch (default: 100).",
    )
    args = parser.parse_args()

    try:
        reddit = create_reddit_instance()
        posts = list(fetch_posts(reddit, args.query, args.subreddit, args.limit))

        if not posts:
            logging.warning("No posts found for the given query. Exiting.")
            return

        # Generate a dynamic filename
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        safe_query = "".join(
            c if c.isalnum() else "_" for c in args.query.lower().replace(" ", "_")
        )
        filename = f"{safe_query}_{args.subreddit}_{timestamp}.json"

        save_to_json(posts, filename)

    except (ValueError, Exception) as e:
        logging.critical(f"A critical error occurred: {e}")


if __name__ == "__main__":
    main()
