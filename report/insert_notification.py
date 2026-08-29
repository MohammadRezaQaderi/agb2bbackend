"""
Notification insertion script with static configuration.

This script inserts notifications into the notifications table that are displayed
in the dashboard. It uses static configuration to define notification data.
"""
import os
import sys
from typing import List, Dict, Any, Optional

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from helper.db.sqlalchemy.queries.other import create_notification
from helper.db.sqlalchemy.session import session_scope


# Static notification configuration
# Each notification is a dictionary with the following fields:
# - roles: Target roles (e.g., 'institute', 'school', 'ownerConsultant', 'con', 'all')
# - user_id: Specific user ID (optional, None for role-based notifications)
# - title: Notification title
# - description: Short description
# - added_by: Who added the notification
# - priority: Priority level (e.g., 'high', 'medium', 'low')
# - persian_date: Persian date string
# - fullText: Full notification text
NOTIFICATIONS_CONFIG = [
    {
        "roles": "all",
        "user_id": None,
        "title": "خوش آمدید",
        "description": "به سیستم هدایت تحصیلی و روان شناسی خوش آمدید",
        "added_by": "سیستم",
        "priority": "medium",
        "persian_date": "1403/01/01",
        "fullText": "به سیستم هدایت تحصیلی و روان شناسی خوش آمدید. لطفا از امکانات سیستم استفاده کنید."
    },
    {
        "roles": "institute",
        "user_id": None,
        "title": "اطلاعیه مهم برای موسسات",
        "description": "لطفا اطلاعات خود را به روز نگه دارید",
        "added_by": "مدیریت",
        "priority": "high",
        "persian_date": "1403/01/15",
        "fullText": "موسسات محترم، لطفا اطلاعات دانش آموزان و مشاوران خود را به طور منظم به روز رسانی کنید."
    },
    {
        "roles": "school",
        "user_id": None,
        "title": "اطلاعیه مدارس",
        "description": "راهنمای استفاده از سیستم",
        "added_by": "پشتیبانی",
        "priority": "medium",
        "persian_date": "1403/01/20",
        "fullText": "مدارس محترم، برای استفاده بهتر از سیستم، راهنمای کاربری را مطالعه فرمایید."
    },
    {
        "roles": "ownerConsultant",
        "user_id": None,
        "title": "اطلاعیه مشاوران",
        "description": "نکات مهم برای مشاوران",
        "added_by": "مدیریت",
        "priority": "high",
        "persian_date": "1403/02/01",
        "fullText": "مشاوران محترم، لطفا در ثبت اطلاعات دانش آموزان دقت لازم را داشته باشید."
    },
    {
        "roles": "con",
        "user_id": None,
        "title": "راهنمای مشاوران",
        "description": "راهنمای استفاده از پنل مشاور",
        "added_by": "پشتیبانی",
        "priority": "medium",
        "persian_date": "1403/02/10",
        "fullText": "مشاوران عزیز، برای استفاده بهتر از پنل مشاور، راهنمای کاربری را مطالعه کنید."
    },
]


def insert_notification(
    roles: str,
    title: str,
    description: str,
    added_by: str,
    priority: str,
    persian_date: str,
    fullText: str,
    user_id: Optional[int] = None,
) -> Optional[int]:
    """
    Insert a notification into the notifications table.

    Args:
        roles: Target roles (e.g., 'institute', 'school', 'ownerConsultant', 'con', 'all').
        title: Notification title.
        description: Short description.
        added_by: Who added the notification.
        priority: Priority level (e.g., 'high', 'medium', 'low').
        persian_date: Persian date string.
        fullText: Full notification text.
        user_id: Specific user ID (optional, None for role-based notifications).

    Returns:
        Notification ID if successful, None otherwise.
    """
    with session_scope() as session:
        return create_notification(
            session=session,
            roles=roles,
            title=title,
            description=description,
            added_by=added_by,
            priority=priority,
            persian_date=persian_date,
            full_text=fullText,
            user_id=user_id,
        )


def insert_notifications_from_config(
    notifications: List[Dict[str, Any]],
    dry_run: bool = False,
) -> Dict[str, Any]:
    """
    Insert notifications from static configuration.

    Args:
        notifications: List of notification dictionaries from config.
        dry_run: If True, don't actually insert into database.

    Returns:
        Dictionary containing insertion summary.
    """
    total_count = len(notifications)
    inserted_count = 0
    error_count = 0
    results = []

    print(f"Starting {'DRY RUN - ' if dry_run else ''}notification insertion process...")
    print(f"Total notifications to process: {total_count}")

    if dry_run:
        print("\n=== DRY RUN MODE - No data will be inserted ===")
        for idx, notification in enumerate(notifications, 1):
            print(f"\n[{idx}/{total_count}] Would insert notification:")
            print(f"  Title: {notification['title']}")
            print(f"  Roles: {notification['roles']}")
            print(f"  User ID: {notification.get('user_id', 'N/A')}")
            print(f"  Priority: {notification['priority']}")
            results.append({
                'title': notification['title'],
                'status': 'Would insert',
                'notification_id': None,
            })
        return {
            'total_count': total_count,
            'inserted_count': 0,
            'error_count': 0,
            'results': results,
            'dry_run': True,
        }

    for idx, notification in enumerate(notifications, 1):
        print(f"\n[{idx}/{total_count}] Inserting notification: {notification['title']}")
        try:
            notification_id = insert_notification(
                roles=notification['roles'],
                title=notification['title'],
                description=notification['description'],
                added_by=notification['added_by'],
                priority=notification['priority'],
                persian_date=notification['persian_date'],
                fullText=notification['fullText'],
                user_id=notification.get('user_id'),
            )
            inserted_count += 1
            results.append({
                'title': notification['title'],
                'status': 'Success',
                'notification_id': notification_id,
            })
            print(f"  ✓ Successfully inserted (ID: {notification_id})")
        except Exception as e:
            error_count += 1
            results.append({
                'title': notification['title'],
                'status': 'Error',
                'notification_id': None,
            })
            print(f"  ✗ Failed to insert: {e}")

    print(f"\n=== INSERTION SUMMARY ===")
    print(f"Total notifications: {total_count}")
    print(f"Successfully inserted: {inserted_count}")
    print(f"Errors encountered: {error_count}")
    if total_count > 0:
        print(f"Success rate: {(inserted_count / total_count) * 100:.1f}%")

    return {
        'total_count': total_count,
        'inserted_count': inserted_count,
        'error_count': error_count,
        'results': results,
        'dry_run': False,
    }


def print_summary(result: Dict[str, Any]) -> None:
    """
    Print a summary of the insertion process.

    Args:
        result: Result dictionary from insert_notifications_from_config.
    """
    print("\n" + "=" * 50)
    print("QUICK SUMMARY")
    print("=" * 50)
    print(f"Total Notifications: {result['total_count']}")
    action = "Would insert" if result.get('dry_run') else "Inserted"
    print(f"Successfully {action}: {result['inserted_count']}")
    print(f"Errors: {result['error_count']}")
    if result['total_count'] > 0 and not result.get('dry_run'):
        print(f"Success Rate: {(result['inserted_count'] / result['total_count']) * 100:.1f}%")

    errors = [r for r in result['results'] if r['status'] == 'Error']
    if errors:
        print(f"\nErrors encountered:")
        for i, error in enumerate(errors, 1):
            print(f"  {i}. {error['title']}")


def main() -> None:
    """Main entry point for the script."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Insert notifications into the database from static configuration",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Insert all notifications from config
  python insert_notification.py

  # Dry run (test without inserting)
  python insert_notification.py --dry-run

  # Show config without inserting
  python insert_notification.py --show-config
        """
    )

    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Process without inserting into database',
    )
    parser.add_argument(
        '--show-config',
        action='store_true',
        help='Show notification configuration and exit',
    )

    args = parser.parse_args()

    if args.show_config:
        print("=== NOTIFICATION CONFIGURATION ===")
        print(f"Total notifications in config: {len(NOTIFICATIONS_CONFIG)}\n")
        for idx, notification in enumerate(NOTIFICATIONS_CONFIG, 1):
            print(f"[{idx}] {notification['title']}")
            print(f"    Roles: {notification['roles']}")
            print(f"    User ID: {notification.get('user_id', 'N/A')}")
            print(f"    Priority: {notification['priority']}")
            print(f"    Description: {notification['description']}")
            print()
        return

    try:
        result = insert_notifications_from_config(
            notifications=NOTIFICATIONS_CONFIG,
            dry_run=args.dry_run,
        )
        print_summary(result)
    except Exception as e:
        print(f"✗ Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
