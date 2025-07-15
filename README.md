# HN Tags

Tooling to associate semantic tags with Hacker News stories

## Usage

I'm using [uv](https://docs.astral.sh/uv/) so this will be something like `uv run main.py` - however since this 
is not so much "in-progress" as "barely started and clearly unfinished" that's a bit academic for now.

When finished this will parse the Hacker News feed and dump the results as one or more html etc. files suitable
for use as static content on the [hntags.com](https://hntags.com/) website.

## Status

  * Cleaner categorisation
  * Renders category pages
  * Renders something that looks a bit like an HN page
  * Uses an Ollama client to categorise the stories 
  * Lists all the top story IDs

## Notes

I'm currently using the [Firebase](https://pypi.org/project/firebase/) library to connect to 
the [Hacker News firebase feed](https://github.com/HackerNews/API?tab=readme-ov-file). This is not a current
or official library; however, its last update was reasonably recent (2023) and it supports anonymous
credentials - which as far as I can work out the official Google Firebase client/admin libraries don't.

I'm using [Jinja 2](https://jinja.palletsprojects.com/) to template the HN style and I've pulled down a 
copy of their front page to be a starting point for the template.

I'm using the [Gemma3n model](https://ollama.com/library/gemma3n) because it runs at a reasonable speed on my
little Linux machine without a GPU.

Next up is to figure out exactly how I'm going to serve these pages and set that up - I want to use CloudFront
but not sure exactly how I'm going to manage the atomic switching of the content if I push it to S3 instead
of a real filesystem. Perhaps I'll just run a micro instance with nginx on it or something?