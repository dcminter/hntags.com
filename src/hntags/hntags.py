from firebase.firebase import FirebaseApplication
from typing import NamedTuple
from ollama import Client
from hntags import hn_firebase
from hntags import llm
import datetime


class Ingestion(NamedTuple):
    max_stories: int
    max_comments: int
    max_categories: int


def process_comments(
    firebase: FirebaseApplication,
    classifier: llm.Classifier,
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
        comment_texts = []
        comment_count = len(comment_ids)
        print(f"Retrieving {comment_count} comment_texts", end="", flush=True)
        for index, comment_id in enumerate(comment_ids):
            print(".", end="", sep="", flush=True)
            raw_comment = hn_firebase.get_raw_comment(firebase, comment_id)
            comment_text = f"""Comment ID: {comment_id}, By: {raw_comment.get("by")}, Time: {raw_comment.get("time")}, Score: {raw_comment.get("score")}, Dead: {raw_comment.get("dead")}, Deleted: {raw_comment.get("deleted")}
                    {raw_comment.get("text") or ""}"""
            comment_texts.append(comment_text)
        print()

        print("All comment_texts retrieved for this story")
        raw_story["tags"] = llm.categorise_story_and_comments(
            classifier=classifier,
            story_text=story_text,
            comment_texts=comment_texts,
            max_categories=max_categories,
        )
        raw_story["comment_count"] = comment_count
        return raw_story
    else:
        print(
            f"Story is dead or deleted ({raw_story.get('dead')}/{raw_story.get('deleted')})"
        )
        return None


def retrieve_and_categorise_stories(
    firebase: FirebaseApplication,
    classifier: llm.Classifier,
    ingestion: Ingestion,
    start_time_utc: datetime,
):
    story_ids = hn_firebase.get_top_story_ids(
        firebase=firebase, max_stories=ingestion.max_stories
    )
    stories = []
    categorised_stories = {}

    for index, story_id in enumerate(story_ids):  # Should I be using map here really?
        print(
            f"Elapsed time so far: {(datetime.datetime.now(datetime.timezone.utc) - start_time_utc).total_seconds()} seconds"
        )
        print(f"Processing comments for story {index + 1} of {ingestion.max_stories}")
        story = process_comments(
            classifier=classifier,
            firebase=firebase,
            story_id=story_id,
            max_comments=ingestion.max_comments,
            max_categories=ingestion.max_categories,
        )

        story["index"] = index
        stories.append(story)

        for tag in story.get("tags") or []:
            entries_in_category = categorised_stories.get(tag) or []
            entries_in_category.append(story)
            categorised_stories[tag] = entries_in_category

    return categorised_stories, stories
