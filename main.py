from firebase import firebase
from ollama import Client
from ollama import ChatResponse
import datetime

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
"AI, Hats, Short Sticks." The output MUST always be in English. The output MUST never contain words other than the 
list of categories itself."""

model = 'gemma3n:e4b' # originally using llama3.3
host = 'http://slab.local:11434' # Originally http://yorkshire.local:11434
threads = 8 # Crude profiling suggests it really is worth using all the available cores on Slab

client = Client(
    host = host,
)

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
    for category in categories:
        print(f"Category: {category}")

    print(f"Short list: {categories[:2]}")

def dump_story(db, id):
    story = db.get('v0/item', id)
    print(f"Retrieved story with id {id} and title '{story.get('title')}'")

    if not story.get('dead') and not story.get('deleted'):
        story_text = f"""Story: {story['title']}, ID: {id}
            By: {story.get('by')}, Time: {story.get('time')}, Score: {story.get('score')}, Dead: {story.get('dead')}, Deleted: {story.get('deleted')}
            {story.get('text') or story.get('url')}"""

        comments = []
        comment_count = len(story.get('comments') or [])
        for index, comment_id  in enumerate(story.get('kids')):
            print(f"Retrieving comment {index} of {comment_count} for this story")
            comment = db.get('v0/item', comment_id)
            comment_text = \
                f"""Comment ID: {comment_id}, By: {comment.get('by')}, Time: {comment.get('time')}, Score: {comment.get('score')}, Dead: {comment.get('dead')}, Deleted: {comment.get('deleted')}
                    {comment.get('text') or ''}"""
            comments.append(comment_text)

        print('All comments retrieved for this story')
        ask_the_llama(story_text, comments)
    else:
        print(f'Story is dead or deleted ({story.get('dead')}/{story.get('deleted')})')

def main():
    db = firebase.FirebaseApplication("https://hacker-news.firebaseio.com/")
    full_top_story_ids = db.get('v0', 'topstories')
    top_story_ids = full_top_story_ids[:60] # Truncate to two pages worth

#    for story_id in top_story_ids:
#        dump_story(db, story_id)
    dump_story(db, top_story_ids[0]) # We'll be doing this for all of them eventually

if __name__ == "__main__":
    main()
