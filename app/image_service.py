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

"""Image generation service for DineLine AI using gemini-3.1-flash-lite-image."""

import inspect
import time
from typing import Any, Dict
from google import genai
from google.genai import types
from google.adk.tools import ToolContext

from .storage_service import GCP_PROJECT_ID, BUCKET_NAME, upload_image_bytes

_genai_client = None


def get_genai_client() -> genai.Client:
    """Returns singleton Google GenAI client targeting global region with hardcoded project ID."""
    global _genai_client
    if _genai_client is None:
        _genai_client = genai.Client(
            vertexai=True,
            project=GCP_PROJECT_ID,
            location="global",
        )
    return _genai_client


async def generate_item_image(
    prompt: str,
    tool_context: ToolContext,
    item_name: str = "dish_visual",
) -> Dict[str, Any]:
    """Generates an image using gemini-3.1-flash-lite-image in the global region.
    
    1. Saves the image as an ADK session artifact via tool_context.save_artifact.
    2. Uploads the image bytes to the public Cloud Storage bucket.
    3. Returns the public HTTPS URL without writing to a local file.
    """
    client = get_genai_client()
    enhanced_prompt = (
        f"Professional culinary and restaurant photography of {prompt}, fine dining aesthetic, 4k"
    )

    response = client.models.generate_content(
        model="gemini-3.1-flash-lite-image",
        contents=enhanced_prompt,
        config=types.GenerateContentConfig(
            response_modalities=["IMAGE"],
        ),
    )

    image_bytes = None
    mime_type = "image/jpeg"

    if response.candidates and response.candidates[0].content and response.candidates[0].content.parts:
        for part in response.candidates[0].content.parts:
            if part.inline_data and part.inline_data.data:
                image_bytes = part.inline_data.data
                mime_type = part.inline_data.mime_type or "image/jpeg"
                break

    if not image_bytes:
        return {
            "success": False,
            "error": "Failed to generate image bytes from model response.",
        }

    # 1. Save as ADK session artifact for Playground Artifacts panel
    safe_name = "".join(c if c.isalnum() else "_" for c in item_name.lower())[:30]
    filename = f"{safe_name}_{int(time.time())}.jpg"
    artifact_part = types.Part.from_bytes(data=image_bytes, mime_type=mime_type)
    
    save_result = tool_context.save_artifact(
        filename=filename,
        artifact=artifact_part,
    )
    if inspect.isawaitable(save_result):
        version = await save_result
    else:
        version = save_result

    # 2. Upload directly to public Cloud Storage bucket
    storage_path = f"generated/{filename}"
    public_url = upload_image_bytes(
        image_bytes=image_bytes,
        filename=storage_path,
        content_type=mime_type,
    )

    return {
        "success": True,
        "item_name": item_name,
        "artifact_filename": filename,
        "artifact_version": version,
        "public_url": public_url,
        "bucket": BUCKET_NAME,
        "message": f"Image generated for '{item_name}', saved to session artifacts as '{filename}', and published to Cloud Storage at {public_url}",
    }
