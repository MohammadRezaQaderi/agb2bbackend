"""
Discount insertion script with static configuration.

This script inserts discount codes into the discounts table. It uses static
configuration to define discount data.
"""
import os
import sys
from datetime import datetime
from typing import List, Dict, Any, Optional

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from helper.db.sqlalchemy.queries.other import create_discount
from helper.db.sqlalchemy.session import session_scope


# Static discount configuration
# Each discount is a dictionary with the following fields:
# - code: Discount code (VARCHAR(10))
# - status: Discount status (e.g., 'active', 'inactive')
# - discount_percentage: Discount percentage (FLOAT)
# - count: Maximum number of uses (INT, default 100)
# - count_apply: Maximum number of applies (INT, default 0)
# - expire_time: Expiration datetime (DATETIME, optional)
DISCOUNTS_CONFIG = [
    {
        "code": "WELCOME10",
        "status": "active",
        "discount_percentage": 10.0,
        "count": 100,
        "count_apply": 0,
        "expire_time": None,
    },
    {
        "code": "STUDENT20",
        "status": "active",
        "discount_percentage": 20.0,
        "count": 50,
        "count_apply": 0,
        "expire_time": "2025-12-31 23:59:59",
    },
    {
        "code": "SUMMER15",
        "status": "active",
        "discount_percentage": 15.0,
        "count": 200,
        "count_apply": 0,
        "expire_time": "2025-08-31 23:59:59",
    },
]


def parse_expire_time(expire_time: Optional[str]) -> Optional[datetime]:
    if not expire_time:
        return None
    return datetime.strptime(expire_time, "%Y-%m-%d %H:%M:%S")


def insert_discount(
    code: str,
    status: str,
    discount_percentage: float,
    count: int = 100,
    count_apply: int = 0,
    expire_time: Optional[str] = None,
) -> Optional[int]:
    """
    Insert a discount into the discounts table.

    Args:
        code: Discount code (VARCHAR(10)).
        status: Discount status (e.g., 'active', 'inactive').
        discount_percentage: Discount percentage (FLOAT).
        count: Maximum number of uses (INT, default 100).
        count_apply: Maximum number of applies (INT, default 0).
        expire_time: Expiration datetime string (optional, format: 'YYYY-MM-DD HH:MM:SS').

    Returns:
        Discount ID if successful, None otherwise.
    """
    with session_scope() as session:
        return create_discount(
            session=session,
            code=code,
            status=status,
            discount_percentage=discount_percentage,
            count=count,
            count_apply=count_apply,
            expire_time=parse_expire_time(expire_time),
        )


def insert_discounts_from_config(
    discounts: List[Dict[str, Any]],
    dry_run: bool = False,
) -> Dict[str, Any]:
    """
    Insert discounts from static configuration.

    Args:
        discounts: List of discount dictionaries from config.
        dry_run: If True, don't actually insert into database.

    Returns:
        Dictionary containing insertion summary.
    """
    total_count = len(discounts)
    inserted_count = 0
    error_count = 0
    results = []

    print(f"Starting {'DRY RUN - ' if dry_run else ''}discount insertion process...")
    print(f"Total discounts to process: {total_count}")

    if dry_run:
        print("\n=== DRY RUN MODE - No data will be inserted ===")
        for idx, discount in enumerate(discounts, 1):
            print(f"\n[{idx}/{total_count}] Would insert discount:")
            print(f"  Code: {discount['code']}")
            print(f"  Status: {discount['status']}")
            print(f"  Discount Percentage: {discount['discount_percentage']}%")
            print(f"  Count: {discount.get('count', 100)}")
            print(f"  Expire Time: {discount.get('expire_time', 'No expiration')}")
            results.append({
                'code': discount['code'],
                'status': 'Would insert',
                'discount_id': None,
            })
        return {
            'total_count': total_count,
            'inserted_count': 0,
            'error_count': 0,
            'results': results,
            'dry_run': True,
        }

    for idx, discount in enumerate(discounts, 1):
        print(f"\n[{idx}/{total_count}] Inserting discount: {discount['code']}")
        try:
            discount_id = insert_discount(
                code=discount['code'],
                status=discount['status'],
                discount_percentage=discount['discount_percentage'],
                count=discount.get('count', 100),
                count_apply=discount.get('count_apply', 0),
                expire_time=discount.get('expire_time'),
            )
            inserted_count += 1
            results.append({
                'code': discount['code'],
                'status': 'Success',
                'discount_id': discount_id,
            })
            print(f"  ✓ Successfully inserted (ID: {discount_id})")
        except Exception as e:
            error_count += 1
            results.append({
                'code': discount['code'],
                'status': 'Error',
                'discount_id': None,
            })
            print(f"  ✗ Failed to insert: {e}")

    print(f"\n=== INSERTION SUMMARY ===")
    print(f"Total discounts: {total_count}")
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
        result: Result dictionary from insert_discounts_from_config.
    """
    print("\n" + "=" * 50)
    print("QUICK SUMMARY")
    print("=" * 50)
    print(f"Total Discounts: {result['total_count']}")
    action = "Would insert" if result.get('dry_run') else "Inserted"
    print(f"Successfully {action}: {result['inserted_count']}")
    print(f"Errors: {result['error_count']}")
    if result['total_count'] > 0 and not result.get('dry_run'):
        print(f"Success Rate: {(result['inserted_count'] / result['total_count']) * 100:.1f}%")

    errors = [r for r in result['results'] if r['status'] == 'Error']
    if errors:
        print(f"\nErrors encountered:")
        for i, error in enumerate(errors, 1):
            print(f"  {i}. {error['code']}")


def main() -> None:
    """Main entry point for the script."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Insert discounts into the database from static configuration",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Insert all discounts from config
  python insert_discount.py

  # Dry run (test without inserting)
  python insert_discount.py --dry-run

  # Show config without inserting
  python insert_discount.py --show-config
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
        help='Show discount configuration and exit',
    )

    args = parser.parse_args()

    if args.show_config:
        print("=== DISCOUNT CONFIGURATION ===")
        print(f"Total discounts in config: {len(DISCOUNTS_CONFIG)}\n")
        for idx, discount in enumerate(DISCOUNTS_CONFIG, 1):
            print(f"[{idx}] {discount['code']}")
            print(f"    Status: {discount['status']}")
            print(f"    Discount Percentage: {discount['discount_percentage']}%")
            print(f"    Count: {discount.get('count', 100)}")
            print(f"    Count Apply: {discount.get('count_apply', 0)}")
            print(f"    Expire Time: {discount.get('expire_time', 'No expiration')}")
            print()
        return

    try:
        result = insert_discounts_from_config(
            discounts=DISCOUNTS_CONFIG,
            dry_run=args.dry_run,
        )
        print_summary(result)
    except Exception as e:
        print(f"✗ Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
