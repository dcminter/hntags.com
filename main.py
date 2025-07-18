from firebase import firebase
from firebase.firebase import FirebaseApplication
from ollama import Client
from ollama import ChatResponse
import datetime
from pathlib import Path
import os

from jinja2 import Environment, PackageLoader, select_autoescape

JINJA2_ENV = Environment(
    loader=PackageLoader("main", "template"), autoescape=select_autoescape()
)

SYSTEM_PROMPT = """
You will be processing text from a popular discussion site (Hacker News) in the format of stories (which may be simple 
URLs or text) and the top-level comments replying to them. You SHOULD infer from the comments and story details a short 
set of comma-separated categories that the story falls into. At MOST five categories should be listed; single-word 
category names are preferable but a category name SHOULD never exceed two words. Thus an absurd example list might be 
"AI, Hats, Short Sticks." Prefer simpler category names; "AI" is preferable to "AI Software" for example. The output 
MUST always be in English. The output MUST never contain words other than the list of categories itself."""

HOST = os.environ.get("HNTAGS_HOST", "http://localhost:11434")
MODEL = os.environ.get("HNTAGS_MODEL", "qwen2.5:1.5b")
THREADS = int(os.environ.get("HNTAGS_THREADS", 8))
STORIES_IN_PAGE = int(os.environ.get("HNTAGS_STORIES", 30))


client = Client(
    host=HOST,
)


def get_stories(db):
    full_top_story_ids = db.get("v0", "topstories")
    top_story_ids = full_top_story_ids[:STORIES_IN_PAGE]
    return top_story_ids


def sanitised_categories(categories):
    categories = [category for category in categories if len(category.split(" ")) <= 2]
    for index, category in enumerate(categories):
        if "/" in category:
            all = category.split("/")
            categories[index : index + 1] = all
    return categories


def ask_the_llama(story, comments):
    context = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": story},
    ]
    for comment in comments:
        context.append({"role": "user", "content": comment})

    start = datetime.datetime.now()
    print(
        f"Making request to ollama (on '{HOST}', with model '{MODEL}' at {start} (Local time)"
    )
    response: ChatResponse = client.chat(
        model=MODEL, options={"num_thread": THREADS}, messages=context
    )
    finish = datetime.datetime.now()
    print(
        f"Response received at {finish} (Local time) taking {(finish - start).total_seconds()} seconds to complete"
    )

    categories = list(map(str.strip, response.message.content.split(",")))
    categories = [category.lower() for category in categories]
    for category in categories:
        print(f"Category: {category}")

    # I constrain this a lot so that (hopefully) we only get genuinely relevant categories
    return sanitised_categories(categories[:3])[:3]


def process_comments(db: FirebaseApplication, id):
    story = db.get("v0/item", id)
    print(f"Retrieved story with id {id} and title '{story.get('title')}'")

    if not story.get("dead") and not story.get("deleted"):
        story_text = f"""Story: {story["title"]}, ID: {id}
            By: {story.get("by")}, Time: {story.get("time")}, Score: {story.get("score")}, Dead: {story.get("dead")}, Deleted: {story.get("deleted")}
            {story.get("text") or story.get("url")}"""

        # It makes no sense to drag in ALL top level comments. Let's truncate it to 10 and assume those cover the gist
        comment_ids = story.get("kids") or []
        comment_ids = comment_ids[:10]
        comments = []
        comment_count = len(comment_ids)
        print(f"Retrieving {comment_count} comments", end="", flush=True)
        for index, comment_id in enumerate(comment_ids):
            print(".", end="", sep="", flush=True)
            comment = db.get("v0/item", comment_id)
            comment_text = f"""Comment ID: {comment_id}, By: {comment.get("by")}, Time: {comment.get("time")}, Score: {comment.get("score")}, Dead: {comment.get("dead")}, Deleted: {comment.get("deleted")}
                    {comment.get("text") or ""}"""
            comments.append(comment_text)
        print()

        print("All comments retrieved for this story")
        story["tags"] = ask_the_llama(story_text, comments)
        story["comment_count"] = comment_count
        return story
    else:
        print(f"Story is dead or deleted ({story.get('dead')}/{story.get('deleted')})")
        return None


def retrieve_and_categorise_stories(starttime):
    db = firebase.FirebaseApplication("https://hacker-news.firebaseio.com/")
    stories = []
    categorised_stories = {}
    for index, story_id in enumerate(
        get_stories(db)
    ):  # Should I be using map here really?
        print(
            f"Elapsed time so far: {(datetime.datetime.now(datetime.timezone.utc) - starttime).total_seconds()} seconds"
        )
        print(f"Processing comments for story {index + 1} of {STORIES_IN_PAGE}")
        story = process_comments(db, story_id)
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
        f"I will connect to {HOST} to run Ollama model {MODEL} with {THREADS} threads and processing {STORIES_IN_PAGE} front page stories"
    )

    start_time_utc = datetime.datetime.now(datetime.timezone.utc)
    print(f"Run started at {start_time_utc} (UTC)")

    categorised_stories, stories = retrieve_and_categorise_stories(start_time_utc)

    # Loading complete, so capture the timestamp to differentiate when we looked at HN and when we finished rendering
    render_time = datetime.datetime.now(datetime.timezone.utc)

    template = JINJA2_ENV.get_template("hntags.html")

    output_path = "./output"
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


if __name__ == "__main__":
    main()
