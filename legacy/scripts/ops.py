import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(REPO_ROOT))

from alembic import command
from alembic.config import Config
from app.core.config import settings
from legacy.services.rich_menu_service import rich_menu_service


def run_migrations(database_url: str | None = None) -> None:
    if database_url:
        settings.DATABASE_URL = database_url
    config_path = REPO_ROOT / "alembic.ini"
    cfg = Config(str(config_path))
    command.upgrade(cfg, "head")


def setup_rich_menus() -> None:
    mappings = rich_menu_service.setup_menus()
    if mappings:
        print("rich menus configured")
        for name, menu_id in mappings.items():
            print(f"- {name}: {menu_id}")
    else:
        print("no menus configured")


def main() -> None:
    parser = argparse.ArgumentParser(description="Operations helpers")
    sub = parser.add_subparsers(dest="command", required=True)

    migrate_parser = sub.add_parser("migrate", help="run alembic upgrade head")
    migrate_parser.add_argument("--database-url", help="override DATABASE_URL for this run")
    sub.add_parser("rich-menus", help="create rich menus from service config")

    args = parser.parse_args()

    if args.command == "migrate":
        run_migrations(args.database_url)
    elif args.command == "rich-menus":
        setup_rich_menus()


if __name__ == "__main__":
    main()
