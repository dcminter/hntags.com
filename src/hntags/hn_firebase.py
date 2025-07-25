from firebase import firebase
from firebase.firebase import FirebaseApplication


def get_hn_firebase_connection():
    return firebase.FirebaseApplication("https://hacker-news.firebaseio.com/")


def get_top_story_ids(firebase: FirebaseApplication, max_stories: int):
    full_top_story_ids = firebase.get("v0", "topstories")
    top_story_ids = full_top_story_ids[:max_stories]
    return top_story_ids


def get_raw_story(firebase: FirebaseApplication, story_id: str):
    return firebase.get("v0/item", story_id)


def get_raw_comment(firebase: FirebaseApplication, comment_id: str):
    return firebase.get("v0/item", comment_id)
