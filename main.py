from firebase import firebase



def main():
    db = firebase.FirebaseApplication("https://hacker-news.firebaseio.com/")
    top_story_ids = db.get('v0', 'topstories')
    print(f"List of {len(top_story_ids)} stories")

    for story_id in top_story_ids:
        print(f"StoryID: {story_id}")

if __name__ == "__main__":
    main()
