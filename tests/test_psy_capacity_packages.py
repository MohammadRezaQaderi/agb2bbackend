from helper.constants import PACKAGES_DATA, PSY_PACKAGE_TITLES
from helper.db.sqlalchemy.models import CapacityPackage
from helper.db.sqlalchemy.queries.students import create_capacity_with_packages
from quiz_packages.psy.generated_manifest import PACKAGE_NAMES


class RecordingSession:
    def __init__(self):
        self.added = []

    def add(self, value):
        self.added.append(value)

    def flush(self):
        return None


def test_all_generated_psy_packages_are_registered():
    assert set(PACKAGE_NAMES) == set(PSY_PACKAGE_TITLES)
    assert all(package_name in PACKAGES_DATA for package_name in PACKAGE_NAMES)


def test_psy_packages_start_with_zero_capacity_for_new_accounts():
    session = RecordingSession()
    package_names = ["AG", "SCL", *PACKAGE_NAMES]

    create_capacity_with_packages(
        session=session,
        user_id=42,
        package_names=package_names,
        initial_allowed_packages={"AG", "SCL"},
    )

    packages = {item.package_name: item for item in session.added if isinstance(item, CapacityPackage)}
    assert packages["AG"].allowed == 1
    assert packages["SCL"].allowed == 1
    assert all(packages[name].allowed == 0 for name in PACKAGE_NAMES)
    assert all(packages[name].total_allowed == 0 for name in PACKAGE_NAMES)
