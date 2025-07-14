from firebase import firebase
from firebase.firebase import FirebaseApplication
from ollama import Client
from ollama import ChatResponse
import datetime

from jinja2 import Environment, PackageLoader, select_autoescape
env = Environment(
    loader=PackageLoader('main', 'template'),
    autoescape=select_autoescape()
)

# I'm going to:
# Truncate this to 60 stories (2 pages)
# Send each one with its comments to the LLM for categorisation (instead of dumping them to the console)
# Dump the title + categories to the console
#
# Once that's working ok I'll get it generating HTML and linking in emoji etc.

system_prompt = """
You will be processing text from a popular discussion site (Hacker News) in the format of stories (which may be simple 
URLs or text) and the top-level comments replying to them. You SHOULD infer from the comments and story details a short 
set of comma-separated categories that the story falls into. At MOST five categories should be listed; single-word 
category names are preferable but a category name SHOULD never exceed two words. Thus an absurd example list might be 
"AI, Hats, Short Sticks." Prefer simpler category names; "AI" is preferable to "AI Software" for example. The output 
MUST always be in English. The output MUST never contain words other than the list of categories itself."""

# Other models tried:
# llama3.3 (only tried on GPU)
# gemma3n:e4b (worked ok on CPU)
model = 'qwen2.5:1.5b'
host = 'http://slab.local:11434' # Originally http://yorkshire.local:11434
threads = 8 # Crude profiling suggests it really is worth using all the available cores on Slab
stories_in_page = 30

client = Client(
    host = host,
)

def get_stories(db):
    full_top_story_ids = db.get('v0', 'topstories')
    top_story_ids = full_top_story_ids[:stories_in_page]
    return top_story_ids

def sanitised_categories(categories):
    categories = [category for category in categories if len(category.split(' ')) <= 2 ]
    return categories

def ask_the_llama(story, comments):
    context = [{'role': 'system', 'content': system_prompt}, {'role': 'user', 'content': story}]
    for comment in comments:
        context.append({ 'role':'user', 'content':comment})

    start = datetime.datetime.now()
    print(f"Making request to ollama (on '{host}', with model '{model}' at {start} (Local time)")
    response: ChatResponse = client.chat(model=model, options={ 'num_thread' : threads }, messages=context)
    finish = datetime.datetime.now()
    print(f"Response received at {finish} (Local time) taking {(finish - start).total_seconds()} seconds to complete")

    categories = list(map(str.strip, response.message.content.split(',')))
    categories = [category.lower() for category in categories]
    for category in categories:
        print(f"Category: {category}")

    return sanitised_categories(categories[:5])

def process_comments(db: FirebaseApplication, id):
    story = db.get('v0/item', id)
    print(f"Retrieved story with id {id} and title '{story.get('title')}'")

    if not story.get('dead') and not story.get('deleted'):
        story_text = f"""Story: {story['title']}, ID: {id}
            By: {story.get('by')}, Time: {story.get('time')}, Score: {story.get('score')}, Dead: {story.get('dead')}, Deleted: {story.get('deleted')}
            {story.get('text') or story.get('url')}"""

        comments = []
        comment_count = len(story.get('kids') or [])
        for index, comment_id  in enumerate(story.get('kids') or []):
            print(f"Retrieving comment {index} of {comment_count} for this story")
            comment = db.get('v0/item', comment_id)
            comment_text = \
                f"""Comment ID: {comment_id}, By: {comment.get('by')}, Time: {comment.get('time')}, Score: {comment.get('score')}, Dead: {comment.get('dead')}, Deleted: {comment.get('deleted')}
                    {comment.get('text') or ''}"""
            comments.append(comment_text)

        print('All comments retrieved for this story')
        story['tags'] = ask_the_llama(story_text, comments)
        story['comment_count'] = comment_count
        return story
    else:
        print(f'Story is dead or deleted ({story.get('dead')}/{story.get('deleted')})')
        return None

def main():
    start = datetime.datetime.now(datetime.timezone.utc)
    print(f"Run started at {start} (UTC)")

    # This block should move to a function
    db = firebase.FirebaseApplication("https://hacker-news.firebaseio.com/")
    stories = []
    categorised_stories = {}
    for index, story_id in enumerate(get_stories(db)): # Should I be using map here really?
        story = process_comments(db, story_id)
        story['index'] = index
        stories.append(story)
        for tag in story.get('tags') or []:
            entries_in_category = categorised_stories.get(tag) or []
            entries_in_category.append(story)
            categorised_stories[tag] = entries_in_category

    # Loading complete, so capture the timestamp to differentiate when we looked at HN and when we finished rendering
    render_time = datetime.datetime.now(datetime.timezone.utc)

    template = env.get_template("hntags.html")

    with open("output/index.html", "w") as output:
        output.write(template.render({
            'page' : stories,
            'render' : render_time,
            'start' : start,
            'category' : 'all'
        }))

    for category in categorised_stories:
        print(f"Category: {category} contains {len(categorised_stories.get(category) or [])} stories")
        with open(f"output/{category}.html", "w") as output:
            output.write(template.render({
                'page' : categorised_stories.get(category) or [],
                'render' : render_time,
                'start' : start,
                'category' : category
            }))

    finish = datetime.datetime.now(datetime.timezone.utc)
    print(f"Run finished at {finish} (Local time) after {(finish - start).total_seconds()} seconds with {len(categorised_stories)} total categories identified.")

    # TODO... push the categories into Ollama and ask it to simplify them - so that things like "AI Software" get squashed to "AI" for another
    # set of index pages!

if __name__ == "__main__":
    main()
