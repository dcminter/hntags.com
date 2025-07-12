from firebase import firebase
from ollama import Client
from ollama import ChatResponse

# I'm going to:
# Truncate this to 60 stories (2 pages)
# Send each one with its comments to the LLM for categorisation (instead of dumping them to the console)
# Dump the title + categories to the console
#
# Once that's working ok I'll get it generating HTML and linking in emoji etc.

system_prompt = """
You will be processing text from a popular discussion site (Hacker News) in the format of stories (which may be simple 
URLs or text) and the top-level comments replying to them. You SHOULD infer from the comments and story details a short 
set of comma-separated catogories that the story falls into. At MOST five categories should be listed; single-word 
category names are preferable but a category name SHOULD never exceed two words. Thus an absurd example list might be 
"AI, Hats, Short Sticks." The output MUST always be in English. The output MUST never contain words other than the 
list of categories itself."""

client = Client(
    host = 'http://yorkshire.local:11434',
)

def ask_the_llama(story, comments):
    context = [{'role': 'system', 'content': system_prompt}, {'role': 'user', 'content': story}]
    for comment in comments:
        context.append({ 'role':'user', 'content':comment})
    response: ChatResponse = client.chat(model='llama3.3', messages=context)
    print(response.message.content) # TODO: Parse this into a list and return that instead (with appropriate error handling)

def dump_story(db, id):
    story = db.get('v0/item', id)

    story_text = f"""Story: {story['title']}, ID: {id}
        By: {story.get('by')}, Time: {story.get('time')}, Score: {story.get('score')}, Dead: {story.get('dead')}, Deleted: {story.get('deleted')}
        {story.get('text') or story.get('url')}"""

    comments = []
    for comment_id in story.get('kids'):
        comment = db.get('v0/item', comment_id)
        comment_text = \
            f"""Comment ID: {comment_id}, By: {comment.get('by')}, Time: {comment.get('time')}, Score: {comment.get('score')}, Dead: {comment.get('dead')}, Deleted: {comment.get('deleted')}
                {comment.get('text') or ''}"""
        comments.append(comment_text)

    ask_the_llama(story_text, comments)

def main():
    db = firebase.FirebaseApplication("https://hacker-news.firebaseio.com/")
    full_top_story_ids = db.get('v0', 'topstories')
    top_story_ids = full_top_story_ids[:60] # Truncate to two pages worth

#    for story_id in top_story_ids:
#        dump_story(db, story_id)
    dump_story(db, top_story_ids[0]) # We'll be doing this for all of them eventually



if __name__ == "__main__":
    main()
