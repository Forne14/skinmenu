from __future__ import annotations

import json
import re
import shutil
import sqlite3
from datetime import datetime
from pathlib import Path
from uuid import uuid4


ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "db.sqlite3"
PLACEHOLDER_SUMMARY = "Add a one-paragraph summary explaining outcomes, suitability, and approach."


def backup_db() -> Path:
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = ROOT / f"db_before_pre_normalised_rebuild_{stamp}.sqlite3"
    shutil.copy2(DB_PATH, backup_path)
    return backup_path


def existing_columns(cursor: sqlite3.Cursor, table: str) -> set[str]:
    rows = cursor.execute(f"PRAGMA table_info({table})").fetchall()
    return {row[1] for row in rows}


def add_column_if_missing(cursor: sqlite3.Cursor, table: str, column_sql: str, name: str) -> None:
    if name not in existing_columns(cursor, table):
        cursor.execute(f"ALTER TABLE {table} ADD COLUMN {column_sql}")


def richtext_to_plain(html: str) -> str:
    if not html:
        return ""
    text = re.sub(r"<[^>]+>", " ", html)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def truncate(text: str, max_length: int) -> str:
    if len(text) <= max_length:
        return text
    return text[: max_length - 1].rstrip() + "…"


def make_block(block_type: str, value: dict) -> dict:
    return {"type": block_type, "value": value, "id": str(uuid4())}


def split_lines(value: str) -> list[str]:
    return [line.strip() for line in (value or "").splitlines() if line.strip()]


def clone_hero_with_headline(hero_json: str, headline: str) -> str:
    if not hero_json:
        return "[]"
    blocks = json.loads(hero_json)
    if blocks and blocks[0].get("type") == "hero_block":
        blocks[0]["value"]["headline"] = headline
    return json.dumps(blocks)


def row_dicts(cursor: sqlite3.Cursor, sql: str, params: tuple = ()) -> list[dict]:
    cursor.execute(sql, params)
    columns = [col[0] for col in cursor.description]
    return [dict(zip(columns, row)) for row in cursor.fetchall()]


def build_products_block(block: dict, items: list[dict]) -> dict:
    products = []
    for item in items:
        products.append(
            {
                "title": item["title"] or "",
                "price": item["price_text"] or "",
                "description": item["body"] or "",
                "targets": split_lines(item["value"]),
                "cta_label": item["cta_label"] or "",
                "cta_url": item["cta_url"] or item["url"] or "",
            }
        )
    return make_block(
        "treatment_products",
        {
            "heading": block["heading"] or "Pricing",
            "products": products,
        },
    )


def build_steps_block(block: dict, items: list[dict]) -> dict:
    steps = []
    for item in items:
        text = item["body"] or ""
        if not text and item["value"]:
            bullets = "".join(f"<p>- {line}</p>" for line in split_lines(item["value"]))
            text = bullets
        steps.append({"title": item["title"] or "", "text": text})
    return make_block(
        "steps",
        {
            "eyebrow": block["eyebrow"] or "",
            "heading": block["heading"] or "What to expect",
            "steps": steps,
        },
    )


def build_cta_block(block: dict) -> dict:
    return make_block(
        "cta",
        {
            "heading": block["heading"] or "Book a consultation",
            "body": block["body"] or "",
            "primary_cta": {
                "label": block["primary_cta_label"] or "Book now",
                "url": block["primary_cta_url"] or "https://portal.aestheticnursesoftware.com/book-online/5695",
            },
            "secondary_cta": (
                {
                    "label": block["secondary_cta_label"],
                    "url": block["secondary_cta_url"],
                }
                if block["secondary_cta_label"] and block["secondary_cta_url"]
                else None
            ),
        },
    )


def build_rich_text_section(heading: str, body: str, eyebrow: str = "") -> dict:
    return make_block(
        "rich_text_section",
        {
            "eyebrow": eyebrow,
            "heading": heading,
            "body": body,
        },
    )


def main() -> None:
    backup_path = backup_db()
    print(f"Backed up current DB to {backup_path}")

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    add_column_if_missing(cursor, "pages_menusectionpage", "featured_image_id integer", "featured_image_id")
    add_column_if_missing(cursor, "pages_menusectionpage", "sections text NOT NULL DEFAULT '[]'", "sections")
    add_column_if_missing(cursor, "pages_treatmentpage", "hero text NOT NULL DEFAULT '[]'", "hero")
    add_column_if_missing(cursor, "pages_treatmentpage", "summary text NOT NULL DEFAULT ''", "summary")
    add_column_if_missing(cursor, "pages_treatmentpage", "featured_image_id integer", "featured_image_id")
    add_column_if_missing(cursor, "pages_treatmentpage", "sections text NOT NULL DEFAULT '[]'", "sections")

    treatments = {
        row["id"]: row
        for row in row_dicts(
            cursor,
            """
            SELECT id, name, slug, summary, long_description, featured_image_id
            FROM catalog_treatment
            ORDER BY id
            """,
        )
    }
    options = {
        row["id"]: row
        for row in row_dicts(
            cursor,
            """
            SELECT id, name, summary, long_description, featured_image_id, treatment_id
            FROM catalog_treatmentoption
            ORDER BY id
            """,
        )
    }

    content_blocks = {
        row["id"]: row
        for row in row_dicts(
            cursor,
            """
            SELECT
                id,
                block_type,
                eyebrow,
                heading,
                body,
                primary_cta_label,
                primary_cta_url,
                secondary_cta_label,
                secondary_cta_url
            FROM catalog_contentblock
            ORDER BY id
            """,
        )
    }

    content_items_by_block: dict[int, list[dict]] = {}
    for row in row_dicts(
        cursor,
        """
        SELECT
            block_id,
            sort_order,
            title,
            body,
            label,
            value,
            url,
            price_text,
            cta_label,
            cta_url
        FROM catalog_contentblockitem
        ORDER BY block_id, sort_order
        """,
    ):
        content_items_by_block.setdefault(row["block_id"], []).append(row)

    treatment_blocks: dict[int, list[dict]] = {}
    for row in row_dicts(
        cursor,
        """
        SELECT treatment_id, block_id, sort_order
        FROM catalog_treatmentcontentblock
        ORDER BY treatment_id, sort_order
        """,
    ):
        treatment_blocks.setdefault(row["treatment_id"], []).append(row)

    option_blocks: dict[int, list[dict]] = {}
    for row in row_dicts(
        cursor,
        """
        SELECT option_id, block_id, sort_order
        FROM catalog_treatmentoptioncontentblock
        ORDER BY option_id, sort_order
        """,
    ):
        option_blocks.setdefault(row["option_id"], []).append(row)

    menu_pages = row_dicts(
        cursor,
        """
        SELECT page_ptr_id, treatment_id, intro, hero
        FROM pages_menusectionpage
        ORDER BY page_ptr_id
        """,
    )
    treatment_pages = row_dicts(
        cursor,
        """
        SELECT page_ptr_id, option_id
        FROM pages_treatmentpage
        ORDER BY page_ptr_id
        """,
    )

    treatment_body_lookup: dict[tuple[int, str], str] = {}
    for treatment_id, links in treatment_blocks.items():
        for link in links:
            block = content_blocks[link["block_id"]]
            if block["block_type"] != "steps":
                continue
            for item in content_items_by_block.get(block["id"], []):
                key = (treatment_id, item["title"].strip().lower())
                treatment_body_lookup[key] = item["body"] or ""

    for menu_page in menu_pages:
        treatment = treatments.get(menu_page["treatment_id"])
        if not treatment:
            continue

        rebuilt_sections = []
        for link in treatment_blocks.get(treatment["id"], []):
            block = content_blocks[link["block_id"]]
            items = content_items_by_block.get(block["id"], [])
            if block["block_type"] == "products" and items:
                rebuilt_sections.append(build_products_block(block, items))
            elif block["block_type"] == "steps" and items:
                rebuilt_sections.append(build_steps_block(block, items))
            elif block["block_type"] == "cta":
                rebuilt_sections.append(build_cta_block(block))

        cursor.execute(
            """
            UPDATE pages_menusectionpage
            SET featured_image_id = ?, sections = ?
            WHERE page_ptr_id = ?
            """,
            (
                treatment["featured_image_id"],
                json.dumps(rebuilt_sections),
                menu_page["page_ptr_id"],
            ),
        )

    parent_menu_by_treatment = {row["treatment_id"]: row for row in menu_pages}
    for treatment_page in treatment_pages:
        option = options.get(treatment_page["option_id"])
        if not option:
            continue

        treatment = treatments.get(option["treatment_id"])
        parent_menu = parent_menu_by_treatment.get(option["treatment_id"])
        option_sections = []

        matched_body = treatment_body_lookup.get((option["treatment_id"], option["name"].strip().lower()), "")
        if matched_body:
            option_sections.append(build_rich_text_section(option["name"], matched_body))
        elif option["long_description"]:
            option_sections.append(build_rich_text_section(option["name"], option["long_description"]))

        for link in option_blocks.get(option["id"], []):
            block = content_blocks[link["block_id"]]
            if block["block_type"] == "cta":
                option_sections.append(build_cta_block(block))

        summary = option["summary"] or ""
        if not summary or summary == PLACEHOLDER_SUMMARY:
            source = matched_body or option["long_description"] or ""
            summary = truncate(richtext_to_plain(source), 240) if source else ""

        hero = clone_hero_with_headline(parent_menu["hero"], option["name"]) if parent_menu else "[]"
        featured_image_id = option["featured_image_id"] or (treatment["featured_image_id"] if treatment else None)

        cursor.execute(
            """
            UPDATE pages_treatmentpage
            SET hero = ?, summary = ?, featured_image_id = ?, sections = ?
            WHERE page_ptr_id = ?
            """,
            (
                hero,
                summary,
                featured_image_id,
                json.dumps(option_sections),
                treatment_page["page_ptr_id"],
            ),
        )

    conn.commit()
    conn.close()
    print("Rebuilt local db.sqlite3 for pre-normalised code.")


if __name__ == "__main__":
    main()
