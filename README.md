# HN Tags

Tooling to associate semantic tags with Hacker News stories

## Usage

I'm using [uv](https://docs.astral.sh/uv/) so this will be something like `uv run main.py` - however since this 
is not so much "in-progress" as "barely started and clearly unfinished" that's a bit academic for now.

When finished this will parse the Hacker News feed and dump the results as one or more html etc. files suitable
for use as static content on the hntags.com website.

## Status

  * Lists all the top story IDs

## Notes

I'm currently using the [Firebase](https://pypi.org/project/firebase/) library to connect to 
the [Hacker News firebase feed](https://github.com/HackerNews/API?tab=readme-ov-file). This is not a current
or official library; however, its last update was reasonably recent (2023) and it supports anonymous
credentials - which as far as I can work out the official Google Firebase client/admin libraries don't.
