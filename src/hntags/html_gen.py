from jinja2 import Environment, Template
from pathlib import Path
import os
import datetime


def write_category_indices(
    categorised_stories, render_time, start, output_path, template: Template
):
    for category in categorised_stories:
        print(
            f"Category: {category} contains {len(categorised_stories.get(category) or [])} stories"
        )
        with open(f"{output_path}/{category}.html", "wb") as output:
            output.write(
                template.render(
                    {
                        "page": categorised_stories.get(category) or [],
                        "render": render_time,
                        "start": start,
                        "category": category,
                    }
                ).encode("utf-8")
            )


def write_main_index(
    render_time_utc: datetime,
    start_time_utc: datetime,
    stories,
    output_path,
    template: Template,
):
    with open(f"{output_path}/index.html", "wb") as output:
        output.write(
            template.render(
                {
                    "page": stories,
                    "render": render_time_utc.strftime("%H:%M:%S %Z"),
                    "start": start_time_utc.strftime("%H:%M:%S %Z"),
                    "category": "all",
                }
            ).encode("utf-8")
        )


def clean_output_directory(path):
    path = Path(path)
    indices = path.glob("*.html")
    for file in indices:
        file.unlink()


def generate(
    environment: Environment, start_time_utc: datetime, stories, categorised_stories
):
    # Capture the timestamp to differentiate when we looked at HN and when we finished rendering
    render_time_utc = datetime.datetime.now(datetime.timezone.utc)

    template: Template = environment.get_template("hntags.html")
    output_path = f"{os.getcwd()}/output"
    print(f"Output path is: {output_path}")
    clean_output_directory(output_path)

    write_main_index(render_time_utc, start_time_utc, stories, output_path, template)
    write_category_indices(
        categorised_stories, render_time_utc, start_time_utc, output_path, template
    )
