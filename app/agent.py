# ruff: noqa
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

"""DineLine AI - Restaurant Queue & Table Concierge Agent."""

import json
from typing import Any, Dict, List, Optional
from google.adk.agents import Agent
from google.adk.agents.callback_context import CallbackContext
from google.adk.apps import App
from google.adk.models import Gemini
from google.adk.tools import ToolContext
from google.adk.tools.preload_memory_tool import PreloadMemoryTool
from google.adk.memory import VertexAiMemoryBankService
from google.adk.code_executors.agent_engine_sandbox_code_executor import (
    AgentEngineSandboxCodeExecutor,
)
from google.genai import types

from .firestore_service import (
    add_to_waitlist,
    get_waitlist,
    get_ticket_status,
    get_all_tables,
    seat_party,
    free_table,
    compute_table_recommendations,
    query_restaurant_menu,
)
from .storage_service import generate_and_upload_qr
from .image_service import generate_item_image

MODEL = "gemini-3.8-flash"
GCP_PROJECT_ID = "qwiklabs-gcp-04-6a213cd4ec79"
LOCATION = "us-east1"

# Memory Bank / Agent Engine runtime ID from deployment_metadata.json
MEMORY_BANK_ID = "6420702604002590720"
AGENT_ENGINE_RUNTIME_ID = (
    f"projects/456383580074/locations/{LOCATION}/reasoningEngines/{MEMORY_BANK_ID}"
)


async def generate_memories_callback(callback_context: CallbackContext):
    """Callback triggered after each turn to extract and persist long-term memories to Vertex AI Memory Bank."""
    await callback_context.add_session_to_memory()
    return None


async def generate_restaurant_item_image(
    item_description: str,
    tool_context: ToolContext,
    item_name: str = "restaurant_special",
) -> str:
    """Generates a high-quality visual for a restaurant dish, cocktail, dessert, or dining ambiance using Gemini image generation.

    The generated image is saved directly into the session artifacts panel and uploaded to the public Cloud Storage bucket.

    Args:
        item_description: Detailed visual description of the dish, drink, or dining scene (e.g. 'Molten lava cake with vanilla ice cream and fresh raspberries', 'Charred Spanish octopus on white ceramic plate').
        tool_context: ADK tool context providing artifact storage for the Playground Artifacts panel.
        item_name: Short name/tag for the item (e.g. 'molten_lava_cake', 'prime_ribeye').

    Returns:
        JSON string containing the public Cloud Storage HTTPS URL (public_url) and artifact details.
    """
    result = await generate_item_image(
        prompt=item_description,
        tool_context=tool_context,
        item_name=item_name,
    )
    return json.dumps(result, indent=2)


def check_restaurant_menu(
    keyword: str = "",
    category: str = "",
    dietary_tag: str = "",
) -> str:
    """Queries the restaurant's official verified menu in Firestore.

    Use this tool to check available dishes, ingredients, dietary options (vegan, vegetarian, gluten-free), and prices.

    Args:
        keyword: Search keyword (e.g., 'salmon', 'truffle', 'ribeye', 'risotto', 'chocolate').
        category: Menu category ('Mains', 'Appetizers', 'Desserts', 'Drinks', or '' for all).
        dietary_tag: Dietary restriction filter ('gluten-free', 'vegetarian', 'vegan', 'pescatarian').

    Returns:
        JSON string containing the restaurant's matching menu dishes with prices, ingredients, and photos.
    """
    dishes = query_restaurant_menu(keyword=keyword, category=category, dietary_tag=dietary_tag)
    return json.dumps({"count": len(dishes), "dishes": dishes}, indent=2)


def generate_checkin_qr_poster(
    target_url: str = "http://localhost:8080/dev-ui/?app=app&role=guest",
) -> str:
    """Generates a branded QR code check-in image for guests and uploads it to public Cloud Storage.

    Args:
        target_url: The web URL that the QR code points to (e.g., guest check-in portal).

    Returns:
        JSON string containing the public image URL (public_url) and target check-in URL.
    """
    result = generate_and_upload_qr(target_url=target_url)
    return json.dumps(result, indent=2)


def recommend_table_assignments() -> str:
    """Evaluates available tables against the current waiting parties to recommend optimal seating matches.

    Uses smart seating heuristics to match party sizes and preferences (e.g. booth/patio) with minimal seat waste.

    Returns:
        JSON string containing recommended party-to-table pairings, match rationale, and floor capacity status.
    """
    results = compute_table_recommendations()
    return json.dumps(results, indent=2)


def join_queue(
    party_name: str,
    party_size: int,
    seating_pref: str = "any",
    special_requests: str = "",
    guest_id: str = "",
) -> str:
    """Adds a guest/party to the live restaurant queue in Firestore.

    Args:
        party_name: Name of the party or guest.
        party_size: Number of guests in the party.
        seating_pref: Seating preference (e.g. 'booth', 'patio', 'indoor', 'window', 'bar', 'any').
        special_requests: Any special needs (e.g. 'high chair', 'wheelchair accessible', 'celebrating birthday').
        guest_id: Optional unique guest identifier.

    Returns:
        JSON string containing the created ticket details (ticket_id, position, est_wait_minutes, status).
    """
    ticket = add_to_waitlist(
        party_name=party_name,
        party_size=party_size,
        seating_pref=seating_pref,
        special_requests=special_requests,
        guest_id=guest_id,
    )
    return json.dumps(ticket, indent=2)


def check_queue_status(ticket_id: str) -> str:
    """Checks the real-time queue position and wait time for a given ticket ID.

    Args:
        ticket_id: The ticket ID assigned when joining the queue (e.g., 'TKT-201').

    Returns:
        JSON string with ticket status, queue position, estimated wait minutes, and assigned table if seated.
    """
    ticket = get_ticket_status(ticket_id)
    if not ticket:
        return json.dumps({"error": f"Ticket '{ticket_id}' was not found in the queue."})
    return json.dumps(ticket, indent=2)


def view_live_waitlist(status_filter: str = "waiting") -> str:
    """Retrieves all parties currently on the restaurant waitlist (Owner/Host tool).

    Args:
        status_filter: Filter by party status ('waiting', 'seated', or '' for all).

    Returns:
        JSON string listing waiting parties with their ticket IDs, party sizes, preferences, and wait positions.
    """
    waitlist = get_waitlist(status_filter=status_filter or None)
    return json.dumps({"count": len(waitlist), "waitlist": waitlist}, indent=2)


def view_restaurant_tables() -> str:
    """Retrieves all predefined restaurant tables, their capacities, types, and current occupancy status.

    Returns:
        JSON string listing all tables with their IDs, capacities, types, and statuses ('available' or 'occupied').
    """
    tables = get_all_tables()
    return json.dumps({"total_tables": len(tables), "tables": tables}, indent=2)


def seat_guest_at_table(ticket_id: str, table_id: str) -> str:
    """Assigns an available table to a waiting guest party, marking them seated and removing them from the active queue.

    Args:
        ticket_id: The ticket ID of the party to seat (e.g., 'TKT-201').
        table_id: The ID of the table to assign (e.g., 'T1', 'T3', 'T5').

    Returns:
        JSON string confirming the seating operation and status update.
    """
    result = seat_party(ticket_id=ticket_id, table_id=table_id)
    return json.dumps(result, indent=2)


def clean_and_free_table(table_id: str) -> str:
    """Marks an occupied or dirty table as clean and available for the next party.

    Args:
        table_id: The ID of the table to free (e.g., 'T2', 'T4').

    Returns:
        JSON string with the update confirmation.
    """
    result = free_table(table_id=table_id)
    return json.dumps(result, indent=2)


# Initialize Code Executor pointing to Agent Engine from deployment_metadata.json
sandbox_executor = AgentEngineSandboxCodeExecutor(
    agent_engine_resource_name=AGENT_ENGINE_RUNTIME_ID
)

root_agent = Agent(
    name="root_agent",
    model=Gemini(
        model=MODEL,
        retry_options=types.HttpRetryOptions(attempts=3),
    ),
    code_executor=sandbox_executor,
    after_agent_callback=generate_memories_callback,
    instruction=(
        "You are DineLine AI, an intelligent Restaurant Queue Concierge & Table Manager.\n\n"
        "You remember guest preferences, dietary requirements, favorite tables/booths, and past visits across conversations.\n"
        "You also have access to a secure Python sandbox code executor to safely run calculations, math, "
        "turnover rates, bill split estimation, and table utilization metrics.\n\n"
        "You operate in two core modes:\n"
        "1. **Guest Mode (Natural Language Host Concierge)**:\n"
        "   - Warmly greet guests checking in. Recall their preferences (e.g., 'Welcome back! We remember you prefer a quiet booth and gluten-free options').\n"
        "   - Parse conversational inputs for party size, seating preferences (booth/patio/window/indoor), "
        "and special requests (high chairs, accessibility, celebrations).\n"
        "   - Use `join_queue` to register them and return their Ticket ID, queue position, and estimated wait.\n"
        "   - Use `check_queue_status` when guests ask how many parties are ahead of them or for wait updates.\n"
        "   - Use `check_restaurant_menu` to answer questions about the restaurant's actual dishes, prices, ingredients, and dietary options.\n"
        "   - Use `generate_restaurant_item_image` when a guest asks what a dish looks like or requests a visual preview of a menu item/special.\n\n"
        "2. **Owner / Host Mode (Seating Intelligence & Management)**:\n"
        "   - Use `generate_checkin_qr_poster` when the owner asks for a check-in QR code or poster for the front stand.\n"
        "   - Use `recommend_table_assignments` when the owner asks who to seat next, for seating suggestions, or table optimization.\n"
        "   - Use Python code execution in the sandbox to calculate table utilization percentages, average wait durations, and seat turn metrics.\n"
        "   - Use `generate_restaurant_item_image` if creating visuals for daily chef specials or promotional posters.\n"
        "   - Use `view_live_waitlist` and `view_restaurant_tables` to monitor the floor.\n"
        "   - Use `seat_guest_at_table` when a party is assigned to a table, and `clean_and_free_table` when a table clears.\n\n"
        "Always communicate clearly, concisely, and provide helpful, friendly service."
    ),
    tools=[
        PreloadMemoryTool(),
        generate_restaurant_item_image,
        check_restaurant_menu,
        generate_checkin_qr_poster,
        recommend_table_assignments,
        join_queue,
        check_queue_status,
        view_live_waitlist,
        view_restaurant_tables,
        seat_guest_at_table,
        clean_and_free_table,
    ],
)


def memory_bank_service_builder():
    """Builds VertexAiMemoryBankService for deployed container runtime."""
    return VertexAiMemoryBankService(
        project=GCP_PROJECT_ID,
        location=LOCATION,
        agent_engine_id=MEMORY_BANK_ID,
    )


app = App(
    root_agent=root_agent,
    name="app",
)
