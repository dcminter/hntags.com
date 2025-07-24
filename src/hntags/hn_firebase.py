from firebase import firebase
from firebase.firebase import FirebaseApplication


def get_hn_firebase_connection():
    return firebase.FirebaseApplication("https://hacker-news.firebaseio.com/")


def get_top_story_ids(db, max_stories):
    full_top_story_ids = db.get("v0", "topstories")
    top_story_ids = full_top_story_ids[:max_stories]
    return top_story_ids


def get_raw_story(db: FirebaseApplication, story_id: str):
    return db.get("v0/item", story_id)


def get_raw_comment(db: FirebaseApplication, comment_id: str):
    return db.get("v0/item", comment_id)
