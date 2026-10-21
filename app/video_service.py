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

"""Video generation service for DineLine AI using Google's Omni model (gemini-omni-flash-preview)."""

import inspect
import time
from typing import Any, Dict
import google.auth
import google.auth.transport.requests
import requests
from google.genai import types
from google.adk.tools import ToolContext

from .storage_service import GCP_PROJECT_ID, BUCKET_NAME, get_storage_client

_auth_creds = None


def _get_auth_token() -> str:
    """Gets and refreshes Google Cloud OAuth2 token."""
    global _auth_creds
    if _auth_creds is None:
        _auth_creds, _ = google.auth.default()
    auth_req = google.auth.transport.requests.Request()
    _auth_creds.refresh(auth_req)
    return _auth_creds.token


async def generate_item_video(
    prompt: str,
    tool_context: ToolContext,
    item_name: str = "dish_video",
    duration_seconds: int = 4,
) -> Dict[str, Any]:
    """Generates a short video for an item using gemini-omni-flash-preview in the global region.

    1. Calls the Interactions API for gemini-omni-flash-preview with direct Cloud Storage output URI delivery.
    2. Downloads the generated video bytes from Cloud Storage.
    3. Saves the video bytes as an ADK session artifact via tool_context.save_artifact.
    4. Ensures the video object in the public bucket is readable and returns the public https URL (https://storage.googleapis.com/<bucket>/<object>).
    """
    token = _get_auth_token()
    interactions_url = (
        f"https://aiplatform.googleapis.com/v1beta1/projects/{GCP_PROJECT_ID}/locations/global/interactions"
    )

    safe_item_name = "".join(c if c.isalnum() else "_" for c in item_name.lower())[:30]
    timestamp = int(time.time())

    enhanced_prompt = (
        f"Cinematic culinary video of {prompt}, professional restaurant presentation, smooth camera motion, 4k"
    )
    clamped_duration = max(3, min(duration_seconds, 10))
    duration_str = f"{clamped_duration}s"

    payload = {
        "model": "gemini-omni-flash-preview",
        "input": [
            {
                "type": "text",
                "text": enhanced_prompt,
            }
        ],
        "response_format": [
            {
                "type": "video",
                "delivery": "uri",
                "gcs_uri": f"gs://{BUCKET_NAME}/videos/",
                "aspect_ratio": "16:9",
                "duration": duration_str,
            }
        ],
        "generation_config": {
            "video_config": {
                "task": "text_to_video",
            }
        },
    }

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }

    response = requests.post(interactions_url, json=payload, headers=headers, timeout=180)
    if response.status_code != 200:
        return {
            "success": False,
            "error": f"Video generation failed with status {response.status_code}: {response.text[:500]}",
        }

    resp_data = response.json()
    generated_gcs_uri = None

    for step in resp_data.get("steps", []):
        if step.get("type") == "model_output":
            for content in step.get("content", []):
                if content.get("type") == "video" and "uri" in content:
                    generated_gcs_uri = content["uri"]
                    break

    if not generated_gcs_uri:
        return {
            "success": False,
            "error": "No generated video URI found in Omni model response.",
            "response": resp_data,
        }

    # Extract blob name from gs://<bucket>/<blob_name>
    blob_name = generated_gcs_uri.replace(f"gs://{BUCKET_NAME}/", "")
    storage_client = get_storage_client()
    bucket = storage_client.bucket(BUCKET_NAME)
    blob = bucket.blob(blob_name)

    # Download bytes directly from bucket to save as session artifact
    video_bytes = blob.download_as_bytes()

    # 1. Save artifact with tool_context.save_artifact
    artifact_filename = f"{safe_item_name}_{timestamp}.mp4"
    artifact_part = types.Part.from_bytes(data=video_bytes, mime_type="video/mp4")

    save_result = tool_context.save_artifact(
        filename=artifact_filename,
        artifact=artifact_part,
    )
    if inspect.isawaitable(save_result):
        version = await save_result
    else:
        version = save_result

    # 2. Public HTTPS URL (https://storage.googleapis.com/<bucket>/<object>)
    public_url = f"https://storage.googleapis.com/{BUCKET_NAME}/{blob_name}"

    return {
        "success": True,
        "item_name": item_name,
        "artifact_filename": artifact_filename,
        "artifact_version": version,
        "public_url": public_url,
        "bucket": BUCKET_NAME,
        "duration": duration_str,
        "message": f"Short video generated for '{item_name}', saved to session artifacts as '{artifact_filename}', and published to Cloud Storage at {public_url}",
    }
