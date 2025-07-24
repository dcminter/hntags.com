from ollama import Client
import datetime

SYSTEM_PROMPT = """
You will be processing text from a popular discussion site (Hacker News) in the format of stories (which may be simple 
URLs or text) and the top-level comments replying to them. You SHOULD infer from the comments and story details a short 
set of comma-separated categories that the story falls into. At MOST five categories should be listed; single-word 
category names are preferable but a category name SHOULD never exceed two words. Thus an absurd example list might be 
"AI, Hats, Short Sticks." Prefer simpler category names; "AI" is preferable to "AI Software" for example. The output 
MUST always be in English. The output MUST never contain words other than the list of categories itself."""


def get_ollama_client(host: str):
    print(f"Establishing connection to Ollama host '{host}'")
    return Client(
        host=host,
    )


def sanitised_categories(categories):
    categories = [category for category in categories if len(category.split(" ")) <= 2]
    for index, category in enumerate(categories):
        if "/" in category:
            all = category.split("/")
            categories[index : index + 1] = all
    return categories


def categorise_story_and_comments(
    ollama_client: Client,
    model: str,
    threads: int,
    story: str,
    comment_texts: list[str],
    max_categories,
):
    context = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": story},
    ]
    for comment_text in comment_texts:
        context.append({"role": "user", "content": comment_text})

    start = datetime.datetime.now()
    print(f"Making request to ollama with model '{model}' at {start} (Local time)")
    ollama_response: ChatResponse = ollama_client.chat(
        model=model, options={"num_thread": threads}, messages=context
    )
    finish = datetime.datetime.now()
    print(
        f"Response received at {finish} (Local time) taking {(finish - start).total_seconds()} seconds to complete"
    )

    categories = list(map(str.strip, ollama_response.message.content.split(",")))
    categories = [category.lower() for category in categories]
    for category in categories:
        print(f"Category: {category}")

    # I constrain this a lot so that (hopefully) we only get genuinely relevant categories
    return sanitised_categories(categories[:max_categories])[:max_categories]
