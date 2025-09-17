import os
import csv
import argparse
from typing import Optional

from app import create_app
from extensions import db
from models import ToolCategory, Tool


def str_to_bool(val: Optional[str]) -> bool:
    if val is None:
        return True  # default to active if column missing/blank
    s = str(val).strip().lower()
    return s in ("1", "true", "yes", "y", "t")


def upsert_row(category_name: str, tool_name: str, description: str) -> str:
    """
    Create or update ToolCategory & Tool. Returns one of: 'created', 'updated', 'skipped'
    """
    # Category
    cat = ToolCategory.query.filter_by(name=category_name).first()
    if not cat:
        cat = ToolCategory(name=category_name.strip())
        db.session.add(cat)
        db.session.flush()  # get cat.id

    # Tool (unique by name per your current schema)
    tool = Tool.query.filter_by(name=tool_name).first()
    if tool:
        changed = False
        # Move tool to a different category if needed
        if tool.category_id != cat.id:
            tool.category = cat
            changed = True
        # Update description if provided and changed
        if description and (tool.description or "").strip() != description.strip():
            tool.description = description.strip()
            changed = True
        return "updated" if changed else "skipped"
    else:
        tool = Tool(name=tool_name.strip(), description=(description or "").strip(), category=cat)
        db.session.add(tool)
        return "created"


def delete_inactive(tool_name: str) -> bool:
    """
    Delete a tool by name if it exists. Returns True if deleted.
    """
    tool = Tool.query.filter_by(name=tool_name).first()
    if tool:
        db.session.delete(tool)
        return True
    return False


def process_csv(path: str, dry_run: bool = False, delete_inactive_rows: bool = False):
    if not os.path.isfile(path):
        raise FileNotFoundError(f"CSV file not found: {path}")

    created = updated = skipped = deleted = 0
    seen_tools = set()

    with open(path, "r", newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        # Validate required headers
        required = {"category_name", "tool_name"}
        missing = [h for h in required if h not in reader.fieldnames]
        if missing:
            raise ValueError(f"CSV missing required columns: {', '.join(missing)}")

        for i, row in enumerate(reader, start=2):  # start=2 to account for header row
            category_name = (row.get("category_name") or "").strip()
            tool_name = (row.get("tool_name") or "").strip()
            description = (row.get("description") or "").strip()
            is_active = str_to_bool(row.get("is_active"))

            if not category_name or not tool_name:
                print(f"Row {i}: skipped (missing category_name or tool_name)")
                skipped += 1
                continue

            seen_tools.add(tool_name)

            if not is_active:
                # Optionally delete inactive
                if delete_inactive_rows:
                    if delete_inactive(tool_name):
                        print(f"Row {i}: deleted (inactive) — {tool_name}")
                        deleted += 1
                    else:
                        print(f"Row {i}: skipped (inactive; not found) — {tool_name}")
                        skipped += 1
                else:
                    print(f"Row {i}: skipped (inactive) — {tool_name}")
                    skipped += 1
                continue

            result = upsert_row(category_name, tool_name, description)
            if result == "created":
                print(f"Row {i}: created — {category_name} :: {tool_name}")
                created += 1
            elif result == "updated":
                print(f"Row {i}: updated — {category_name} :: {tool_name}")
                updated += 1
            else:
                print(f"Row {i}: skipped (no change) — {category_name} :: {tool_name}")
                skipped += 1

    if dry_run:
        db.session.rollback()
    else:
        db.session.commit()

    print("\nSummary:")
    print(f"  created: {created}")
    print(f"  updated: {updated}")
    print(f"  deleted: {deleted}")
    print(f"  skipped: {skipped}")
    if dry_run:
        print("  (dry-run: changes were NOT saved)")


def main():
    parser = argparse.ArgumentParser(description="Seed/Update Tool Categories & Tools from CSV.")
    parser.add_argument(
        "--file",
        "-f",
        required=True,
        help="Path to CSV file (must include headers: category_name, tool_name; optional: description, unit, model_or_tag, is_active)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview changes without committing to the database.",
    )
    parser.add_argument(
        "--delete-inactive",
        action="store_true",
        help="If a row has is_active=false, delete the tool if it exists. (Default is: skip inactive rows)",
    )
    args = parser.parse_args()

    # If you need to override DB URL quickly:
    # os.environ["SQLALCHEMY_DATABASE_URI"] = "sqlite:///tools.db"
    app = create_app()
    with app.app_context():
        process_csv(args.file, dry_run=args.dry_run, delete_inactive_rows=args.delete_inactive)


if __name__ == "__main__":
    main()