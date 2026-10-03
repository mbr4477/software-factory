from __future__ import annotations

import os

import boto3
from botocore.client import Config

from ._artifact_store import ArtifactStore

BUCKET_NAME = "pipeline-artifacts"


class S3ArtifactStore(ArtifactStore):
    def __init__(self, endpoint_url: str, access_key: str, secret_key: str):
        super().__init__()
        self._s3 = boto3.client(
            "s3",
            endpoint_url=endpoint_url,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            region_name="us-east-1",
            config=Config(signature_version="s3v4", s3={"addressing_style": "path"}),
        )

    @staticmethod
    def from_env() -> S3ArtifactStore:
        return S3ArtifactStore(
            os.environ.get("S3_ENDPOINT_URL", "http://localhost:9000"),
            os.environ["S3_ACCESS_KEY"],
            os.environ["S3_SECRET_KEY"],
        )

    def create_bucket_if_not_exists(self):
        try:
            self._s3.create_bucket(Bucket=BUCKET_NAME)
        except self._s3.exceptions.BucketAlreadyOwnedByYou:
            pass

    def put_object(self, key: str, src_path: str):
        self._s3.upload_file(src_path, BUCKET_NAME, key)

    def get_object(self, key: str, dst_path: str):
        self._s3.download_file(BUCKET_NAME, key, dst_path)
