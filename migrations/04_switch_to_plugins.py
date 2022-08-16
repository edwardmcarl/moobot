"""
Specifying max distance in Craigslist search was removed in favor of specifying using a notifier
filter.

This migration changes all craigslist search_specs to no longer include max distance/home lat+long.
"""

import json

from moobot.db.models import DbDiscordNotifier, DbListing
from moobot.db.session import Session


def update_notifiers() -> None:
    updated_count = 0
    with Session() as session:
        db_notifiers: list[DbDiscordNotifier] = session.query(DbDiscordNotifier).all()
        for db_notifier in db_notifiers:
            notifier_json = json.loads(db_notifier.config_json)  # type: ignore
            updated = False
            for search in notifier_json["active_searches"]:
                if "source" not in search["spec"]:
                    continue

                del search["spec"]["source"]
                search["spec"]["plugin_path"] = "plugins.craigslist.plugin:CraigslistPlugin"
                updated = True
                updated_count += 1

            if updated:
                db_notifier.config_json = json.dumps(notifier_json)

        session.commit()

    print(f"Updated {updated_count} searches")


def update_listings() -> None:
    updated_listing_count = 0
    with Session() as session:
        db_listings: list[DbListing] = session.query(DbListing).all()
        for db_listing in db_listings:
            search_spec_json = json.loads(db_listing.search_spec_json)  # type: ignore
            if "source" not in search_spec_json:
                continue

            del search_spec_json["source"]
            search_spec_json["plugin_path"] = "plugins.craigslist.plugin:CraigslistPlugin"
            updated_listing_count += 1
            db_listing.search_spec_json = json.dumps(search_spec_json)

        session.commit()

    print(f"Updated {updated_listing_count} listings")


def main() -> None:
    update_notifiers()
    update_listings()


if __name__ == "__main__":
    main()
