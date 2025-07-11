from firebase import firebase

def dump_comments(db, comments):
    print(f"Descendents: {comments}")
    comment = db.get('v0/item', comments[0])
    print(f"By: {comment.get('by')}, Time: {comment.get('time')}, Score: {comment.get('score')}, Dead: {comment.get('dead')}, Deleted: {comment.get('deleted')}")

def dump_story(db, id):
    story = db.get('v0/item', id)

    print(f"Story: {story['title']}, ID: {id}")
    print(f"By: {story.get('by')}, Time: {story.get('time')}, Score: {story.get('score')}, Dead: {story.get('dead')}, Deleted: {story.get('deleted')}")

    if 'text' in story:
        print(story['text'])
    else:
        print(story['url'])

    if 'kids' in story:
        if len(story['kids']) > 0:
            dump_comments(db, story['kids'])

    print()

def main():
    db = firebase.FirebaseApplication("https://hacker-news.firebaseio.com/")
    top_story_ids = db.get('v0', 'topstories')
    print(f"List of {len(top_story_ids)} stories")
    print('===')
    print()


    for story_id in top_story_ids:
        dump_story(db, story_id)

if __name__ == "__main__":
    main()
