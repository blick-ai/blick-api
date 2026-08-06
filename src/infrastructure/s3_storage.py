import boto3

from domain.ports import IStorageService


class S3StorageService(IStorageService):
    def __init__(self, bucket_name: str, region: str):
        self._bucket = bucket_name
        self._client = boto3.client("s3", region_name=region)

    def upload_image(self, key: str, image_bytes: bytes) -> None:
        self._client.put_object(
            Bucket=self._bucket,
            Key=key,
            Body=image_bytes,
            ContentType="image/jpeg",
        )

    def download_image(self, key: str) -> bytes:
        response = self._client.get_object(Bucket=self._bucket, Key=key)
        return response["Body"].read()

    def delete_image(self, key: str) -> None:
        self._client.delete_object(Bucket=self._bucket, Key=key)

    def generate_presigned_url(self, key: str, expires_in: int = 3600) -> str:
        return self._client.generate_presigned_url(
            "get_object",
            Params={"Bucket": self._bucket, "Key": key},
            ExpiresIn=expires_in,
        )
