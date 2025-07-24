from firebase.firebase import FirebaseApplication
from ollama import Client
from ollama import ChatResponse
import datetime
from pathlib import Path
import os
from hntags import hn_firebase
from hntags import llm

from jinja2 import Environment, PackageLoader, select_autoescape

JINJA2_ENV = Environment(
    loader=PackageLoader("hntags", "template"), autoescape=select_autoescape()
)

MODEL_HOST = os.environ.get("HNTAGS_HOST", "http://localhost:11434")
MODEL = os.environ.get("HNTAGS_MODEL", "qwen2.5:1.5b")
THREADS = int(os.environ.get("HNTAGS_THREADS", 8))
STORIES_IN_PAGE = int(os.environ.get("HNTAGS_STORIES", 30))
MAX_CATEGORIES = int(os.environ.get("HNTAGS_CATEGORIES", 3))
MAX_COMMENTS = int(os.environ.get("HNTAGS_COMMENTS", 10))


def get_stories(db):
    full_top_story_ids = db.get("v0", "topstories")
    top_story_ids = full_top_story_ids[:STORIES_IN_PAGE]
    return top_story_ids


def process_comments(
    ollama_client, firebase: FirebaseApplication, story_id: str, max_comments: int
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
            ollama_client, MODEL, THREADS, story_text, comments, MAX_CATEGORIES
        )
        raw_story["comment_count"] = comment_count
        return raw_story
    else:
        print(
            f"Story is dead or deleted ({raw_story.get('dead')}/{raw_story.get('deleted')})"
        )
        return None


def retrieve_and_categorise_stories(starttime):
    firebase = hn_firebase.get_hn_firebase_connection()
    ollama_client = llm.get_ollama_client(MODEL_HOST)
    story_ids = hn_firebase.get_top_story_ids(firebase, STORIES_IN_PAGE)
    stories = []
    categorised_stories = {}
    for index, story_id in enumerate(story_ids):  # Should I be using map here really?
        print(
            f"Elapsed time so far: {(datetime.datetime.now(datetime.timezone.utc) - starttime).total_seconds()} seconds"
        )
        print(f"Processing comments for story {index + 1} of {STORIES_IN_PAGE}")
        story = process_comments(ollama_client, firebase, story_id, MAX_COMMENTS)
        story["index"] = index
        stories.append(story)
        for tag in story.get("tags") or []:
            entries_in_category = categorised_stories.get(tag) or []
            entries_in_category.append(story)
            categorised_stories[tag] = entries_in_category
    return categorised_stories, stories


def clean_output_directory(path):
    path = Path(path)
    indices = path.glob("*.html")
    for file in indices:
        file.unlink()


def write_category_indices(
    categorised_stories, render_time, start, output_path, template
):
    for category in categorised_stories:
        print(
            f"Category: {category} contains {len(categorised_stories.get(category) or [])} stories"
        )
        with open(f"{output_path}/{category}.html", "w") as output:
            output.write(
                template.render(
                    {
                        "page": categorised_stories.get(category) or [],
                        "render": render_time,
                        "start": start,
                        "category": category,
                    }
                )
            )


def write_main_index(render_time, start, stories, output_path, template):
    # Move this stuff into a "writing output" function
    with open(f"{output_path}/index.html", "w") as output:
        output.write(
            template.render(
                {
                    "page": stories,
                    "render": render_time,
                    "start": start,
                    "category": "all",
                }
            )
        )


def main():
    print(
        f"I will connect to {MODEL_HOST} to run Ollama model {MODEL} with {THREADS} threads and processing {STORIES_IN_PAGE} front page stories"
    )

    start_time_utc = datetime.datetime.now(datetime.timezone.utc)
    print(f"Run started at {start_time_utc} (UTC)")

    categorised_stories, stories = retrieve_and_categorise_stories(start_time_utc)

    # Loading complete, so capture the timestamp to differentiate when we looked at HN and when we finished rendering
    render_time = datetime.datetime.now(datetime.timezone.utc)

    template = JINJA2_ENV.get_template("hntags.html")

    output_path = f"{os.getcwd()}/output"
    print(f"Output path is: {output_path}")
    clean_output_directory(output_path)
    write_main_index(render_time, start_time_utc, stories, output_path, template)
    write_category_indices(
        categorised_stories, render_time, start_time_utc, output_path, template
    )

    # I'm going to want a "publish" step here

    finish = datetime.datetime.now(datetime.timezone.utc)
    print(
        f"Run finished at {finish} (Local time) after {(finish - start_time_utc).total_seconds()} seconds with {len(categorised_stories)} total categories identified."
    )


# I am clueless... is this necessary/useful?
if __name__ == "__main__":
    main()
