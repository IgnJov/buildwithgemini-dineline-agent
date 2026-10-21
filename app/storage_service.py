# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Storage service for DineLine AI to generate QR posters and upload to Cloud Storage."""

import io
import time
import qrcode
from google.cloud import storage

GCP_PROJECT_ID = "qwiklabs-gcp-04-6a213cd4ec79"
BUCKET_NAME = f"dineline-assets-{GCP_PROJECT_ID}"

_storage_client = None


def get_storage_client() -> storage.Client:
    """Returns singleton Storage Client instance initialized with hardcoded project ID."""
    global _storage_client
    if _storage_client is None:
        _storage_client = storage.Client(project=GCP_PROJECT_ID)
    return _storage_client


def generate_and_upload_qr(
    target_url: str = "http://localhost:8080/dev-ui/?app=app&role=guest",
    filename_prefix: str = "checkin_qr",
) -> dict:
    """Generates a QR code image for a target URL and uploads it to the public Cloud Storage bucket.

    Args:
        target_url: The check-in URL encoded into the QR code.
        filename_prefix: Prefix for the generated file.

    Returns:
        dict with public_url, bucket, filename, and target_url.
    """
    # 1. Generate QR Code image
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=10,
        border=4,
    )
    qr.add_data(target_url)
    qr.make(fit=True)

    img = qr.make_image(fill_color="#1A73E8", back_color="white")  # Google Blue branded QR
    img_byte_arr = io.BytesIO()
    img.save(img_byte_arr, format="PNG")
    img_byte_arr.seek(0)

    # 2. Upload to Cloud Storage
    client = get_storage_client()
    bucket = client.bucket(BUCKET_NAME)
    filename = f"qr/{filename_prefix}_{int(time.time())}.png"
    blob = bucket.blob(filename)
    blob.upload_from_file(img_byte_arr, content_type="image/png")

    public_url = f"https://storage.googleapis.com/{BUCKET_NAME}/{filename}"
    return {
        "success": True,
        "target_url": target_url,
        "public_url": public_url,
        "filename": filename,
        "bucket": BUCKET_NAME,
        "message": f"Check-in QR code generated and available at {public_url}",
    }


def upload_image_bytes(
    image_bytes: bytes,
    filename: str,
    content_type: str = "image/jpeg",
) -> str:
    """Uploads raw image bytes directly to the public Cloud Storage bucket and returns the public URL."""
    client = get_storage_client()
    bucket = client.bucket(BUCKET_NAME)
    blob = bucket.blob(filename)
    blob.upload_from_string(image_bytes, content_type=content_type)
    return f"https://storage.googleapis.com/{BUCKET_NAME}/{filename}"
