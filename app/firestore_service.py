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

"""Firestore backend service for DineLine AI.

Hardcodes the GCP project ID string to ensure reliable operation across local
development and deployed Agent Platform environments.
"""

import datetime
from typing import Any, Dict, List, Optional
from google.cloud import firestore

# Hardcoded GCP Project ID string to prevent Agent Platform project number resolution issue
GCP_PROJECT_ID = "qwiklabs-gcp-04-6a213cd4ec79"

_db: Optional[firestore.Client] = None


def get_db() -> firestore.Client:
    """Returns a singleton Firestore client instance initialized with the hardcoded project ID."""
    global _db
    if _db is None:
        _db = firestore.Client(project=GCP_PROJECT_ID)
    return _db


# Collections
WAITLIST_COLLECTION = "waitlist"
TABLES_COLLECTION = "tables"


def add_to_waitlist(
    party_name: str,
    party_size: int,
    seating_pref: str = "any",
    special_requests: str = "",
    guest_id: str = "",
) -> Dict[str, Any]:
    """Adds a party to the live waitlist in Firestore."""
    db = get_db()
    now = datetime.datetime.now(datetime.timezone.utc)
    
    # Calculate initial position based on waiting parties
    waiting_docs = list(
        db.collection(WAITLIST_COLLECTION)
        .where("status", "==", "waiting")
        .stream()
    )
    position = len(waiting_docs) + 1
    est_wait_minutes = position * 8  # heuristic: ~8 min per queue position

    doc_ref = db.collection(WAITLIST_COLLECTION).document()
    ticket_id = doc_ref.id[:8].upper()

    ticket_data = {
        "ticket_id": ticket_id,
        "party_name": party_name,
        "party_size": party_size,
        "seating_pref": seating_pref,
        "special_requests": special_requests,
        "guest_id": guest_id or f"guest_{ticket_id.lower()}",
        "status": "waiting",  # waiting, called, seated, cancelled
        "created_at": now.isoformat(),
        "est_wait_minutes": est_wait_minutes,
        "assigned_table": None,
    }

    doc_ref.set(ticket_data)
    ticket_data["id"] = doc_ref.id
    ticket_data["position"] = position
    return ticket_data


def get_waitlist(status_filter: Optional[str] = "waiting") -> List[Dict[str, Any]]:
    """Retrieves waitlist parties sorted by creation timestamp."""
    db = get_db()
    query = db.collection(WAITLIST_COLLECTION)
    if status_filter:
        query = query.where("status", "==", status_filter)

    results = []
    for doc in query.stream():
        data = doc.to_dict()
        data["id"] = doc.id
        results.append(data)

    results.sort(key=lambda x: x.get("created_at", ""))
    for idx, item in enumerate(results, start=1):
        item["position"] = idx
    return results


def get_ticket_status(ticket_id: str) -> Optional[Dict[str, Any]]:
    """Gets real-time position and status for a specific ticket."""
    db = get_db()
    # Search by ticket_id or document id
    docs = list(db.collection(WAITLIST_COLLECTION).where("ticket_id", "==", ticket_id.upper()).stream())
    if not docs:
        doc = db.collection(WAITLIST_COLLECTION).document(ticket_id).get()
        if doc.exists:
            docs = [doc]

    if not docs:
        return None

    target_doc = docs[0]
    target_data = target_doc.to_dict()
    target_data["id"] = target_doc.id

    if target_data.get("status") == "waiting":
        all_waiting = get_waitlist(status_filter="waiting")
        for item in all_waiting:
            if item.get("ticket_id") == target_data.get("ticket_id"):
                target_data["position"] = item.get("position", 1)
                break
    return target_data


def get_all_tables() -> List[Dict[str, Any]]:
    """Retrieves all predefined restaurant tables and their status."""
    db = get_db()
    tables = []
    for doc in db.collection(TABLES_COLLECTION).stream():
        t = doc.to_dict()
        t["id"] = doc.id
        tables.append(t)
    tables.sort(key=lambda x: x.get("table_number", 0))
    return tables


def seat_party(ticket_id: str, table_id: str) -> Dict[str, Any]:
    """Seats a party at a table and removes them from the active waiting queue."""
    db = get_db()
    docs = list(db.collection(WAITLIST_COLLECTION).where("ticket_id", "==", ticket_id.upper()).stream())
    if not docs:
        doc_ref = db.collection(WAITLIST_COLLECTION).document(ticket_id)
        doc = doc_ref.get()
        if not doc.exists:
            return {"success": False, "error": f"Ticket '{ticket_id}' not found."}
    else:
        doc_ref = docs[0].reference

    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    doc_ref.update({
        "status": "seated",
        "assigned_table": table_id,
        "seated_at": now,
    })

    # Update table status to occupied
    table_doc_ref = db.collection(TABLES_COLLECTION).document(table_id)
    table_doc_ref.set({
        "status": "occupied",
        "current_ticket_id": ticket_id.upper(),
        "occupied_at": now,
    }, merge=True)

    return {
        "success": True,
        "ticket_id": ticket_id.upper(),
        "table_id": table_id,
        "message": f"Party with ticket {ticket_id.upper()} has been seated at table {table_id}.",
    }


def free_table(table_id: str) -> Dict[str, Any]:
    """Frees an occupied table and marks it available for the next party."""
    db = get_db()
    table_doc_ref = db.collection(TABLES_COLLECTION).document(table_id)
    table_doc = table_doc_ref.get()
    if not table_doc.exists:
        return {"success": False, "error": f"Table '{table_id}' not found."}

    table_doc_ref.set({
        "status": "available",
        "current_ticket_id": None,
        "freed_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    }, merge=True)

    return {
        "success": True,
        "table_id": table_id,
        "message": f"Table {table_id} is now clean and available.",
    }


def compute_table_recommendations() -> Dict[str, Any]:
    """Evaluates available tables against waiting parties to produce optimal seating matches.

    Matching heuristics:
    1. Table must be available.
    2. Table capacity >= party size.
    3. Minimize seat waste (capacity - party_size).
    4. Prioritize matches satisfying guest seating_pref (booth, patio, indoor, etc.).
    5. Prioritize earlier arrival times (FIFO queue position).
    """
    tables = get_all_tables()
    available_tables = [t for t in tables if t.get("status") == "available"]
    waiting_parties = get_waitlist(status_filter="waiting")

    recommendations = []
    matched_table_ids = set()
    matched_ticket_ids = set()

    for party in waiting_parties:
        ticket_id = party.get("ticket_id")
        party_size = party.get("party_size", 1)
        seating_pref = (party.get("seating_pref") or "any").lower()

        # Find best available table for this party
        candidate_tables = [
            t for t in available_tables
            if t["id"] not in matched_table_ids and t.get("capacity", 0) >= party_size
        ]

        if not candidate_tables:
            continue

        def score_table(t: Dict[str, Any]) -> int:
            score = 0
            capacity = t.get("capacity", 0)
            t_type = (t.get("type") or "").lower()

            # Capacity fit penalty (lower difference is better)
            seat_waste = capacity - party_size
            score -= seat_waste * 10

            # Preference bonus
            if seating_pref != "any":
                if seating_pref in t_type or (seating_pref == "patio" and "patio" in t_type) or (seating_pref == "booth" and "booth" in t_type):
                    score += 50

            return score

        # Sort candidate tables by best score
        candidate_tables.sort(key=score_table, reverse=True)
        best_table = candidate_tables[0]

        matched_table_ids.add(best_table["id"])
        matched_ticket_ids.add(ticket_id)

        recommendations.append({
            "ticket_id": ticket_id,
            "party_name": party.get("party_name"),
            "party_size": party_size,
            "seating_pref": party.get("seating_pref"),
            "special_requests": party.get("special_requests"),
            "recommended_table": {
                "id": best_table["id"],
                "table_number": best_table.get("table_number"),
                "capacity": best_table.get("capacity"),
                "type": best_table.get("type"),
            },
            "match_reason": (
                f"Table {best_table['id']} ({best_table.get('capacity')}-top, {best_table.get('type')}) "
                f"optimally accommodates party of {party_size} with {best_table.get('capacity') - party_size} empty seats."
            ),
        })

    unmatched_parties = [p for p in waiting_parties if p.get("ticket_id") not in matched_ticket_ids]
    unmatched_tables = [t for t in available_tables if t["id"] not in matched_table_ids]

    return {
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "total_available_tables": len(available_tables),
        "total_waiting_parties": len(waiting_parties),
        "recommendations_count": len(recommendations),
        "recommendations": recommendations,
        "unmatched_parties_count": len(unmatched_parties),
        "unmatched_parties": [
            {"ticket_id": p.get("ticket_id"), "party_name": p.get("party_name"), "party_size": p.get("party_size"), "reason": "No suitably sized available table currently"}
            for p in unmatched_parties
        ],
        "remaining_free_tables": [
            {"id": t["id"], "capacity": t.get("capacity"), "type": t.get("type")}
            for t in unmatched_tables
        ],
    }


MENU_COLLECTION = "menu"


def query_restaurant_menu(
    keyword: str = "",
    category: str = "",
    dietary_tag: str = "",
) -> List[Dict[str, Any]]:
    """Queries the restaurant's verified menu in Firestore by keyword, category, or dietary restriction."""
    db = get_db()
    query = db.collection(MENU_COLLECTION)

    items = []
    for doc in query.stream():
        d = doc.to_dict()
        d["id"] = doc.id
        
        # Filter available only
        if not d.get("is_available", True):
            continue

        # Filter category if specified
        if category and category.lower() != "all":
            if (d.get("category") or "").lower() != category.lower():
                continue

        # Filter dietary tag if specified
        if dietary_tag:
            tags = [t.lower() for t in d.get("dietary_tags", [])]
            if dietary_tag.lower() not in tags:
                continue

        # Filter keyword match
        if keyword:
            kw = keyword.lower()
            name_match = kw in (d.get("name") or "").lower()
            desc_match = kw in (d.get("description") or "").lower()
            ing_match = any(kw in ing.lower() for ing in d.get("ingredients", []))
            if not (name_match or desc_match or ing_match):
                continue

        items.append(d)

    return items
