from firebase.firebase import FirebaseApplication
from ollama import Client
from hntags import hn_firebase
from hntags import llm
import datetime


def process_comments(
    ollama_client: Client,
    firebase: FirebaseApplication,
    model: str,
    threads: int,
    story_id: str,
    max_comments: int,
    max_categories: int,
):
    raw_story = hn_firebase.get_raw_story(firebase, story_id)
    print(f"Retrieved story with id {story_id} and title '{raw_story.get('title')}'")

    if not raw_story.get("dead") and not raw_story.get("deleted"):
        story_text = f"""Story: {raw_story["title"]}, ID: {story_id}
            By: {raw_story.get("by")}, Time: {raw_story.get("time")}, Score: {raw_story.get("score")}, Dead: {raw_story.get("dead")}, Deleted: {raw_story.get("deleted")}
            {raw_story.get("text") or raw_story.get("url")}"""

        # It makes no sense to drag in ALL top level comments. Let's truncate it to max_comments and assume those cover the gist
        comment_ids = raw_story.get("kids") or []
        comment_ids = comment_ids[:max_comments]
        comments = []
        comment_count = len(comment_ids)
        print(f"Retrieving {comment_count} comments", end="", flush=True)
        for index, comment_id in enumerate(comment_ids):
            print(".", end="", sep="", flush=True)
            raw_comment = hn_firebase.get_raw_comment(firebase, comment_id)
            comment_text = f"""Comment ID: {comment_id}, By: {raw_comment.get("by")}, Time: {raw_comment.get("time")}, Score: {raw_comment.get("score")}, Dead: {raw_comment.get("dead")}, Deleted: {raw_comment.get("deleted")}
                    {raw_comment.get("text") or ""}"""
            comments.append(comment_text)
        print()

        print("All comments retrieved for this story")
        raw_story["tags"] = llm.categorise_story_and_comments(
            ollama_client, model, threads, story_text, comments, max_categories
        )
        raw_story["comment_count"] = comment_count
        return raw_story
    else:
        print(
            f"Story is dead or deleted ({raw_story.get('dead')}/{raw_story.get('deleted')})"
        )
        return None


def retrieve_and_categorise_stories(
    model_host: str,
    model: str,
    threads: int,
    stories_in_page: int,
    max_comments: int,
    max_categories: int,
    start_time_utc: datetime,
):
    firebase = hn_firebase.get_hn_firebase_connection()
    ollama_client = llm.get_ollama_client(model_host)
    story_ids = hn_firebase.get_top_story_ids(firebase, stories_in_page)
    stories = []
    categorised_stories = {}
    for index, story_id in enumerate(story_ids):  # Should I be using map here really?
        print(
            f"Elapsed time so far: {(datetime.datetime.now(datetime.timezone.utc) - start_time_utc).total_seconds()} seconds"
        )
        print(f"Processing comments for story {index + 1} of {stories_in_page}")
        story = process_comments(
            ollama_client=ollama_client,
            firebase=firebase,
            model=model,
            threads=threads,
            story_id=story_id,
            max_comments=max_comments,
            max_categories=max_categories,
        )
        story["index"] = index
        stories.append(story)
        for tag in story.get("tags") or []:
            entries_in_category = categorised_stories.get(tag) or []
            entries_in_category.append(story)
            categorised_stories[tag] = entries_in_category
    return categorised_stories, stories
