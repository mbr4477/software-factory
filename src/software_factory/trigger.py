import argparse

import yaml

from .hatchet_provider import hatchet
from .pipeline import pipeline_def_from_dict


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("pipeline_def", type=str, help="path to pipeline yaml file")
    args = parser.parse_args()

    with open(args.pipeline_def, "r") as pipeline_file:
        pipeline_dict = yaml.safe_load(pipeline_file)

    pipeline = pipeline_def_from_dict(pipeline_dict)

    hatchet.event.push("pipeline-task", pipeline.model_dump())
