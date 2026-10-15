"""Infrastructure adapters: object storage and email. Real implementations plus in-memory fakes for tests."""

from __future__ import annotations

import smtplib
from email.message import EmailMessage
from typing import Protocol


class ObjectStore(Protocol):
    def put(self, key: str, data: bytes, content_type: str) -> None: ...
    def get(self, key: str) -> bytes: ...
    def delete_prefix(self, prefix: str) -> int: ...
    def total_bytes(self) -> int: ...


class MemoryObjectStore:
    def __init__(self) -> None:
        self.objects: dict[str, bytes] = {}

    def put(self, key: str, data: bytes, content_type: str) -> None:
        self.objects[key] = data

    def get(self, key: str) -> bytes:
        return self.objects[key]

    def delete_prefix(self, prefix: str) -> int:
        keys = [k for k in self.objects if k.startswith(prefix)]
        for k in keys:
            del self.objects[k]
        return len(keys)

    def total_bytes(self) -> int:
        return sum(len(v) for v in self.objects.values())


class S3ObjectStore:
    """S3-compatible storage: MinIO locally, Supabase Storage (S3 protocol) in the cloud. Private bucket."""

    def __init__(self, *, endpoint: str, region: str, access_key: str, secret_key: str, bucket: str) -> None:
        import boto3

        self._bucket = bucket
        self._s3 = boto3.client(
            "s3",
            endpoint_url=endpoint,
            region_name=region,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
        )

    def ensure_bucket(self) -> None:
        names = {b["Name"] for b in self._s3.list_buckets().get("Buckets", [])}
        if self._bucket not in names:
            self._s3.create_bucket(Bucket=self._bucket)

    def put(self, key: str, data: bytes, content_type: str) -> None:
        self._s3.put_object(Bucket=self._bucket, Key=key, Body=data, ContentType=content_type)

    def get(self, key: str) -> bytes:
        body: bytes = self._s3.get_object(Bucket=self._bucket, Key=key)["Body"].read()
        return body

    def delete_prefix(self, prefix: str) -> int:
        n = 0
        for page in self._s3.get_paginator("list_objects_v2").paginate(Bucket=self._bucket, Prefix=prefix):
            objs = [{"Key": o["Key"]} for o in page.get("Contents", [])]
            if objs:
                self._s3.delete_objects(Bucket=self._bucket, Delete={"Objects": objs})
                n += len(objs)
        return n

    def total_bytes(self) -> int:
        total = 0
        for page in self._s3.get_paginator("list_objects_v2").paginate(Bucket=self._bucket):
            total += sum(int(o["Size"]) for o in page.get("Contents", []))
        return total


class Mailer(Protocol):
    def send(self, *, to: str, subject: str, text: str) -> None: ...


class MemoryMailer:
    def __init__(self) -> None:
        self.sent: list[dict[str, str]] = []

    def send(self, *, to: str, subject: str, text: str) -> None:
        self.sent.append({"to": to, "subject": subject, "text": text})


class SmtpMailer:
    """Local Mailpit (no auth, no TLS). SES is added at milestone M9."""

    def __init__(self, host: str, port: int, sender: str) -> None:
        self._host, self._port, self._from = host, port, sender

    def send(self, *, to: str, subject: str, text: str) -> None:
        msg = EmailMessage()
        msg["From"], msg["To"], msg["Subject"] = self._from, to, subject
        msg.set_content(text)
        with smtplib.SMTP(self._host, self._port, timeout=10) as s:
            s.send_message(msg)
