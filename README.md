# HN Tags

Tooling to associate semantic tags with Hacker News stories

## Usage

You can run this in various ways; easiest for local use is to use [`uv`](https://docs.astral.sh/uv/)  in which case
it can be run with `uv run hntags` - once you've set the appropriate [environment variables](#environment-variables).

Alternatively, I'm pushing a suitable docker image as `ghcr.io/dcminter/hntags` - these are tagged with the commit
hash, but the most recent is always `ghcr.io/dcminter/hntags:latest` - as such something like the following
incantation (including environment variables) should work too:

```bash
docker run \
  -e HNTAGS_HOST=<HOSTNAME> \
  -e HNTAGS_THREADS=8 \
  -e HNTAGS_STORIES=30 \
  -e HNTAGS_COMMENTS=5 \
  -e HNTAGS_MODEL=qwen2.5:1.5b \
  -e BUCKET_NAME=<BUCKET> \
  -e DISTRIBUTION_ID=<DISTRIBUTION> \
  -e AWS_DEFAULT_REGION=<REGION> \
  -e AWS_ACCESS_KEY_ID=<ACCESSKEYID> \
  -e AWS_SECRET_ACCESS_KEY=<ACCESSKEY> \
  ghcr.io/dcminter/hntags:latest
```

Inside the Docker image, however, the tool is run by doing a `uv sync` to update the Python virtual environment, then 
activating that and running the hntags command - i.e.

```bash
uv sync
source .venv/bin/activate
hntags
```

## Environment variables

The tool is configurable via the following environment variables:

| Variable         | Default                  | Meaning                                                                                                                     |
|------------------|--------------------------|-----------------------------------------------------------------------------------------------------------------------------|
| `HNTAGS_HOST`    | `http://localhost:11434` | The Ollama server to connect to                                                                                             |
| `HNTAGS_THREADS` | `8`                      | The number of threads to instruct Ollama to use (I find matching the number of cores is usually best with my default model) |
| `HNTAGS_STORIES` | `30`                     | The number of stories to process for the rendered output - 30 is the number on the HN front page                            |
| `HNTAGS_COMMENTS` | `10`                    | The number of top-level comments to take into account when deciding what category to place the story into                   |
| `HNTAGS_MODEL`    | `qwen2.5:1.5b`          | The Ollama model to use - this one works well for this simple task and is small enough for an underwhelming CPU             |
| `BUCKET_NAME`     | -                       | Must be explicitly set. The S3 bucket into which the content will be pushed.                                                |
| `DISTRIBUTION_ID` | -                       | Must be explicitly set. The CloudFront distribution that will be invalidated after the push to S3 is complete.              |

I'm using [Boto3](https://boto3.amazonaws.com/v1/documentation/api/latest/index.html) from AWS to do the cloud
operations (push files to S3 and invalidate the CloudFront distribution). That allows for [various mechanisms for
the library to be configured](https://boto3.amazonaws.com/v1/documentation/api/1.14.23/guide/configuration.html), 
but as I'm running on a machine outside AWS I'm setting the following standard AWS environment variables:

| Variable                | Default | Meaning                                                                                                                  |
|-------------------------|---------|--------------------------------------------------------------------------------------------------------------------------|
| `AWS_DEFAULT_REGION`    | -       | The AWS Region for any AWS resources to be used when accessing via boto3                                                 |
| `AWS_ACCESS_KEY_ID`     | -       | The ID of the access key to be used to do the S3 push and CloudFront distribution invalidation                           |
| `AWS_SECRET_ACCESS_KEY` | -       | The secret access key to be used - this **MUST BE KEPT SECRET, DO NOT CHECK THIS VALUE INTO YOUR REPOSITORY OR LOG IT!** |

## Status

*Not* yet running regularly or automatically. 

  * Publishes to AWS directly (instead of external scripts)
  * Restructured into modules as it was getting a bit unwieldy
  * I'm testing out the infrastructure, so a stale version is public on [HNTags.com](https://hntags.com) right now!
  * Cleaner categorisation
  * Renders category pages
  * Renders something that looks a bit like an HN page
  * Uses an Ollama client to categorise the stories 
  * Lists all the top story IDs

## Prompt

I wouldn't say I was entirely comfortable with our brave new LLM future just yet - the circumstance where I politely
ask the computer to do stuff for me rather than writing a bunch of code is a bit weird. It's quite cool though. Here's
the prompt I'm using for the categorisation:

> You will be processing text from a popular discussion site (Hacker News) in the format of stories (which may be simple 
URLs or text) and the top-level comments replying to them. You SHOULD infer from the comments and story details a short 
set of comma-separated categories that the story falls into. At MOST five categories should be listed; single-word 
category names are preferable but a category name SHOULD never exceed two words. Thus an absurd example list might be 
"AI, Hats, Short Sticks." Prefer simpler category names; "AI" is preferable to "AI Software" for example. The output 
MUST always be in English. The output MUST never contain words other than the list of categories itself.

It's quite "talking to the Enterprise computer" feeling, even if I slipped into RFC-ese a bit there. The behaviour is
reasonable given the underpowered model that I use.

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

I'm using [Boto3](https://boto3.amazonaws.com/v1/documentation/api/latest/index.html) from AWS for the cloud operations.

I'm serving [hntags.com](https://hntags.com) via Cloudfront from an S3 bucket.  Writing all the files to the S3 bucket isn't 
atomic. I don't invalidate the distribution until after I've uploaded all the files to S3 though, so only a user for
whom the files are not in CloudFront's cache will ever see that. It's a bit janky, but will do for now. I may improve
this later by adjusting the update to upload the `index.html` file after the category files.

A side effect is that I'm slowly filling my S3 bucket with stale category pages. I should create a batch job
to go and delete those periodically. I did consider setting up two different S3 buckets (or folders within the bucket)
and changing the distribution origin after each set of files is uploaded - then I could empty the inactive 
bucket/folder after each push. However that feels like a potentially fragile approach and it's probably solving for
a problem (an expensive amount of data in the bucket) that I'll never really have. S3 is very cheap. We'll see.

It occurred to me that if I end up with a category of "index" then I would overwrite my front page! I modified so 
that the front page is generated last, so worst case we'll end up with the "index" category pointing at the front
page instead of a dedicated category page. Uh. Let's call that an easter egg and hope it never happens.

Bugfix: ~~I saw an encoding issue on a story; an em-dash got displayed as `â€“` in story 44561516 so that needs 
a proper fix. That will likely come *after* the work to get it regularly and automatically publishing though.~~ the
files served from the S3 bucket weren't declared as using the UTF-8 charset as part of the content type header. I've
therefore added a meta tag in the template to declare this inline. Oh and I later realised that the reason S3 wasn't 
returning the desired charset in the content type was that I hadn't told it to when uploading the file via the AWS CLI.
This is *also* fixed in the boto3 based uploading now - but I left the meta tag in the template as a belt & braces fix.

I think I want to dockerise this stuff before I fully commit to running it on an hourly basis (the plan).

It would be nice to create some proper tests, although it's definitely more fun not doing that :) 