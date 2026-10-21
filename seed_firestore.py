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

"""Seed script for DineLine AI Firestore database.

Seeds predefined restaurant tables and sample waitlist entries using hardcoded project ID.
"""

import datetime
from google.cloud import firestore

GCP_PROJECT_ID = "qwiklabs-gcp-04-6a213cd4ec79"


def seed():
    print(f"Connecting to Firestore with hardcoded project ID: {GCP_PROJECT_ID}...")
    db = firestore.Client(project=GCP_PROJECT_ID)
    now = datetime.datetime.now(datetime.timezone.utc)

    # 1. Seed Predefined Restaurant Tables
    tables = [
        {"id": "T1", "table_number": 1, "capacity": 2, "type": "indoor_window", "status": "available"},
        {"id": "T2", "table_number": 2, "capacity": 2, "type": "indoor_standard", "status": "occupied", "current_ticket_id": "TKT-100"},
        {"id": "T3", "table_number": 3, "capacity": 4, "type": "booth", "status": "available"},
        {"id": "T4", "table_number": 4, "capacity": 4, "type": "booth", "status": "occupied", "current_ticket_id": "TKT-101"},
        {"id": "T5", "table_number": 5, "capacity": 6, "type": "patio_outdoor", "status": "available"},
        {"id": "T6", "table_number": 6, "capacity": 8, "type": "private_dining", "status": "available"},
    ]

    print("Seeding restaurant tables collection ('tables')...")
    for t in tables:
        doc_id = t["id"]
        table_data = dict(t)
        table_data["updated_at"] = now.isoformat()
        db.collection("tables").document(doc_id).set(table_data)
        print(f"  ✓ Table {doc_id} ({t['capacity']}-top, {t['type']}, status: {t['status']})")

    # 2. Seed Sample Waitlist Entries
    sample_parties = [
        {
            "ticket_id": "TKT-201",
            "party_name": "Sarah Miller",
            "party_size": 2,
            "seating_pref": "booth",
            "special_requests": "Anniversary celebration",
            "guest_id": "guest_sarah",
            "status": "waiting",
            "created_at": (now - datetime.timedelta(minutes=15)).isoformat(),
            "est_wait_minutes": 10,
            "assigned_table": None,
        },
        {
            "ticket_id": "TKT-202",
            "party_name": "David Chen",
            "party_size": 4,
            "seating_pref": "patio_outdoor",
            "special_requests": "Needs 1 high chair",
            "guest_id": "guest_david",
            "status": "waiting",
            "created_at": (now - datetime.timedelta(minutes=8)).isoformat(),
            "est_wait_minutes": 20,
            "assigned_table": None,
        },
        {
            "ticket_id": "TKT-203",
            "party_name": "Elena Rostova",
            "party_size": 5,
            "seating_pref": "any",
            "special_requests": "Vegetarian menu questions",
            "guest_id": "guest_elena",
            "status": "waiting",
            "created_at": (now - datetime.timedelta(minutes=2)).isoformat(),
            "est_wait_minutes": 30,
            "assigned_table": None,
        },
    ]

    print("\nSeeding live waitlist collection ('waitlist')...")
    for p in sample_parties:
        doc_id = p["ticket_id"]
        db.collection("waitlist").document(doc_id).set(p)
        print(f"  ✓ Ticket {p['ticket_id']} for {p['party_name']} (Party of {p['party_size']}, pref: {p['seating_pref']})")

    print("\n✅ Firestore seeding completed successfully!")


if __name__ == "__main__":
    seed()


def seed_menu():
    db = firestore.Client(project=GCP_PROJECT_ID)
    now = datetime.datetime.now(datetime.timezone.utc)

    # 3. Seed Restaurant Menu Items
    menu_items = [
        {
            "id": "dish_1",
            "name": "Pan-Seared Crispy Salmon",
            "category": "Mains",
            "price": 28.50,
            "dietary_tags": ["gluten-free", "pescatarian"],
            "ingredients": ["Atlantic salmon", "asparagus", "lemon herb butter", "garlic mash"],
            "description": "Wild-caught Atlantic salmon seared with crispy skin, served over garlic mashed potatoes and grilled asparagus.",
            "image_url": "https://images.unsplash.com/photo-1467003909585-2f8a72700288?w=800",
            "is_available": True,
        },
        {
            "id": "dish_2",
            "name": "Truffle Mushroom Risotto",
            "category": "Mains",
            "price": 24.00,
            "dietary_tags": ["vegetarian", "gluten-free"],
            "ingredients": ["Arborio rice", "porcini mushrooms", "white truffle oil", "parmesan", "thyme"],
            "description": "Creamy arborio risotto infused with slow-simmered wild porcini mushrooms, finished with white truffle oil.",
            "image_url": "https://images.unsplash.com/photo-1633964913295-ceb43826e7c9?w=800",
            "is_available": True,
        },
        {
            "id": "dish_3",
            "name": "Prime Dry-Aged Ribeye (12oz)",
            "category": "Mains",
            "price": 42.00,
            "dietary_tags": ["gluten-free", "high-protein"],
            "ingredients": ["USDA Prime ribeye", "rosemary compound butter", "roasted fingerling potatoes"],
            "description": "35-day dry-aged USDA Prime ribeye grilled over oak wood, basted with rosemary butter.",
            "image_url": "https://images.unsplash.com/photo-1544025162-d76694265947?w=800",
            "is_available": True,
        },
        {
            "id": "dish_4",
            "name": "Wood-Fired Burrata & Heirloom Tomato",
            "category": "Appetizers",
            "price": 16.00,
            "dietary_tags": ["vegetarian"],
            "ingredients": ["Italian burrata", "heirloom tomatoes", "aged balsamic glaze", "basil pesto", "sourdough crostini"],
            "description": "Creamy Pugliese burrata cheese paired with fresh heirloom tomatoes, sweet basil pesto, and charred sourdough.",
            "image_url": "https://images.unsplash.com/photo-1592417817098-8f3d69109853?w=800",
            "is_available": True,
        },
        {
            "id": "dish_5",
            "name": "Charred Octopus Carpaccio",
            "category": "Appetizers",
            "price": 18.50,
            "dietary_tags": ["gluten-free", "pescatarian"],
            "ingredients": ["Mediterranean octopus", "smoked paprika", "capers", "citrus olive oil"],
            "description": "Tender Spanish octopus thinly sliced, tossed with smoked paprika, crispy capers, and Meyer lemon emulsion.",
            "image_url": "https://images.unsplash.com/photo-1541544741938-0af808871cc0?w=800",
            "is_available": True,
        },
        {
            "id": "dish_6",
            "name": "Decadent Molten Lava Cake",
            "category": "Desserts",
            "price": 12.00,
            "dietary_tags": ["vegetarian"],
            "ingredients": ["Valrhona dark chocolate", "vanilla bean gelato", "fresh raspberries"],
            "description": "Warm dark chocolate cake with a molten chocolate center, served with artisanal Madagascar vanilla gelato.",
            "image_url": "https://images.unsplash.com/photo-1606313564200-e75d5e30476c?w=800",
            "is_available": True,
        },
        {
            "id": "dish_7",
            "name": "House Smoked Old Fashioned",
            "category": "Drinks",
            "price": 15.00,
            "dietary_tags": ["vegan", "gluten-free"],
            "ingredients": ["Small-batch Bourbon", "Angostura bitters", "demerara sugar", "charred orange peel", "cherrywood smoke"],
            "description": "Craft bourbon smoked tableside with cherrywood chips, hand-cut crystal ice sphere.",
            "image_url": "https://images.unsplash.com/photo-1514362545857-3bc16c4c7d1b?w=800",
            "is_available": True,
        },
    ]

    print("\nSeeding restaurant verified menu collection ('menu')...")
    for item in menu_items:
        doc_id = item["id"]
        item_data = dict(item)
        item_data["updated_at"] = now.isoformat()
        db.collection("menu").document(doc_id).set(item_data)
        tags_str = ", ".join(item["dietary_tags"])
        print(f"  ✓ [{item['category']}] {item['name']} - ${item['price']:.2f} ({tags_str})")


if __name__ == "__main__":
    seed()
    seed_menu()
