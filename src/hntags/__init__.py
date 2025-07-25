from ollama import Client
from ollama import ChatResponse
import datetime
import os
from hntags import hn_firebase
from hntags import llm
from hntags import html_gen
from hntags import hntags

from jinja2 import Environment, PackageLoader, select_autoescape

JINJA2_ENV = Environment(
    loader=PackageLoader("hntags", "template"), autoescape=select_autoescape()
)

MODEL_HOST = os.environ.get("HNTAGS_HOST", "http://localhost:11434")
MODEL = os.environ.get("HNTAGS_MODEL", "qwen2.5:1.5b")
THREADS = int(os.environ.get("HNTAGS_THREADS", 8))
STORIES_IN_PAGE = int(os.environ.get("HNTAGS_STORIES", 30))
MAX_COMMENTS = int(os.environ.get("HNTAGS_COMMENTS", 10))
MAX_CATEGORIES = int(os.environ.get("HNTAGS_CATEGORIES", 3))


def main():
    print(
        f"I will connect to {MODEL_HOST} to run Ollama model {MODEL} with {THREADS} threads and processing {STORIES_IN_PAGE} front page stories"
    )

    start_time_utc = datetime.datetime.now(datetime.timezone.utc)
    print(f"Run started at {start_time_utc} (UTC)")

    # Retrieve & categorise the stories
    firebase = hn_firebase.get_hn_firebase_connection()
    classifier = llm.Classifier(
        client=llm.get_ollama_client(MODEL_HOST), model=MODEL, threads=THREADS
    )

    categorised_stories, stories = hntags.retrieve_and_categorise_stories(
        firebase=firebase,
        classifier=classifier,
        stories_in_page=STORIES_IN_PAGE,
        max_comments=MAX_COMMENTS,
        max_categories=MAX_CATEGORIES,
        start_time_utc=start_time_utc,
    )

    # Generate the output files into a working directory (always `./output` relative to the working directory)
    html_gen.generate(JINJA2_ENV, start_time_utc, stories, categorised_stories)

    # I'm going to want a "publish" step here

    finish = datetime.datetime.now(datetime.timezone.utc)
    print(
        f"Run finished at {finish} (Local time) after {(finish - start_time_utc).total_seconds()} seconds with {len(categorised_stories)} total categories identified."
    )


# I am clueless... is this necessary/useful?
if __name__ == "__main__":
    main()
