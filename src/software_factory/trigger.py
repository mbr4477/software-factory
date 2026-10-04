import argparse
import os

import yaml

from .pipeline import pipeline_def_from_dict
from .tasks import pipeline_task


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("pipeline_def", type=str, help="path to pipeline yaml file")
    parser.add_argument(
        "-e", type=str, action="append", help="environment variable definitions"
    )
    args = parser.parse_args()

    with open(args.pipeline_def, "r") as pipeline_file:
        pipeline_dict = yaml.safe_load(pipeline_file)

    pipeline = pipeline_def_from_dict(pipeline_dict)
    if args.e:
        if not pipeline.variables:
            pipeline.variables = {}

        for expr in args.e:
            if "=" in expr:
                name, val = expr.split("=", 1)
                pipeline.variables[name] = val
            else:
                pipeline.variables[expr] = os.environ.get(expr, "")

    pipeline_task.run(pipeline)
