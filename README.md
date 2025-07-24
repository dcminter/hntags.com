# HN Tags

Tooling to associate semantic tags with Hacker News stories

## Usage

I'm using [uv](https://docs.astral.sh/uv/) so this will be something like `uv run hntags` - though I do plan to dockerise this
at some point.

When finished this will parse the Hacker News feed and dump the results as one or more html etc. files suitable
for use as static content on the [hntags.com](https://hntags.com/) website.

## Environment variables

The tool is configurable via the following environment variables:

| Variable         | Default                  | Meaning |
|------------------|--------------------------| --- |
| `HNTAGS_HOST`    | `http://localhost:11434` | The Ollama server to connect to |
| `HNTAGS_THREADS` | `8`                      | The number of threads to instruct Ollama to use (I find matching the number of cores is usually best with my default model) |
| `HNTAGS_STORIES` | `30`                     | The number of stories to process for the rendered output - 30 is the number on the HN front page |
| `HNTAGS_COMMENTS` | `10`                     | The number of top-level comments to take into account when deciding what category to place the story into |
| `HNTAGS_MODEL`    | `qwen2.5:1.5b`           | The Ollama model to use - this one works well for this simple task and is small enough for an underwhelming CPU |



## Status

*Not* yet running regularly or automatically. 

  * Restructured into modules as it was getting a bit unwieldy
  * I'm testing out the infrastructure, so a stale version is public on [HNTags.com](https://hntags.com) right now!
  * Cleaner categorisation
  * Renders category pages
  * Renders something that looks a bit like an HN page
  * Uses an Ollama client to categorise the stories 
  * Lists all the top story IDs

## Bugs

I saw an encoding issue on a story; an em-dash got displayed as `â€“` in story 44561516 so that needs a proper fix.
That will likely come *after* the work to get it regularly and automatically publishing though.

## Weaknesses, Fear, Uncertainty, Doubt

This is mostly an excercise to get myself more up to speed on Python. It kinda works, but I'm sure it's not what
a proper production python application ought to look like. Tips and advice are welcome.

I'm using Ollama for text classification, which is not insane, but I doubt it's the most efficient way to achieve
that goal. Again, I want to learn more about coding with LLMs so that's not a huge problem, but I'll probably 
switch over to something more efficient in the future so my poor little NUC isn't generating a heat haze all the time.

Given that I don't really know what I'm doing with LLMs I'm being a bit paranoid about the text returned from the 
model - rather than trust it to generate sensible stuff I'm treating anything that doesn't parse to short comma
separated lists as garbage and discarding them. That means the categories are a bit off when this happens; the model 
might choose "AI Robot Arms" and I'll chuck it away because it's broken the two-word rule on categories. If the next
category in the list is something bland or weird it'll look like the model did a worse job categorising than it really
did.

I haven't figured out a way to prompt the model to be fairly broad in its categories. For example it will often
categorise one story as "AI Software" and another as "AI Development" and so on, where really I'd like them all
to come under the generic "AI" topic. I tried putting another pass with a prompt to distill down the categories 
to the common topics, but I ended up getting pretty random lists and often they were longer than the original (I
guess once it gets a bunch of comma-separated input it can't resist generating voluminous comma separated output
as the most probable sequence).

The processing takes about 20 to 30 seconds in the typical case. I retrieve the list of top stories and I categorise 
each story after I've retrieved its content and some of the comments on it. This is good in that I won't thrash the 
HN Firebase API, but not so good in that the list of "real" top stories is likely to be very different by the time
I'm ready to render the output. This doesn't seem a big deal for something that's essentially a toy.

~~On one occasion I saw the model get "stuck" for 20 minutes or so. I should set up some logic to just give up
after some reasonable timeout on any individual story so that I don't blow my time budget before the next run
starts (I plan to run it hourly).~~ I set a timeout of 120 seconds on the classification; anything longer than 
that will be treated as no categories.

I don't have any logic in place to check for obnoxiously large top level comments - I should probably discard 
any comment over a maximum length. That might be the cause of the "stuck" modelling actually.

I'm trusting the content of the story title and the first 10 top level comments to be adequate to characterise
the topic of the story. Works pretty well on all my test runs, so I'm going to stick with that (though I might
reduce the number of comments to speed things up a bit if the output still seems more-or-less accurate)

Someone ingenious can probably create a top level comment that messes with my output in ghastly ways; that
will be interesting! Please tell me if you succeeded...

## Notes

I'm currently using the [Firebase](https://pypi.org/project/firebase/) library to connect to 
the [Hacker News firebase feed](https://github.com/HackerNews/API?tab=readme-ov-file). This is not a current
or official library; however, its last update was reasonably recent (2023) and it supports anonymous
credentials - which as far as I can work out the official Google Firebase client/admin libraries don't.

I'm using [Jinja 2](https://jinja.palletsprojects.com/) to template the HN style and I've pulled down a 
copy of their front page to be a starting point for the template.

I'm using the [Qwen2.5:1.5b model](https://www.ollama.com/library/qwen2.5:1.5b) because it runs at a reasonable speed 
on my little Linux machine without a GPU.

I'm serving [hntags.com](https://hntags.com) via Cloudfront from an S3 bucket. Currently I just have a shell script
that uploads the files and creates an invalidation, but I'll move that logic into another python module soon.

I think I want to dockerise this stuff before I fully commit to running it on an hourly basis (the plan).

It would be nice to create some proper tests, although it's definitely more fun not doing that :) 