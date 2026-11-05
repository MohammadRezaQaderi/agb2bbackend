"""Registry for quiz package content providers."""

from helper.quiz_engine.contracts import QuizPackageProvider


def normalize_package_name(package_name: str) -> str:
    normalized = str(package_name or "").strip().upper()
    if not normalized:
        raise ValueError("package_name is required")
    return normalized


class QuizPackageRegistry:
    def __init__(self) -> None:
        self._providers: dict[str, QuizPackageProvider] = {}

    def register(self, provider: QuizPackageProvider, *, replace: bool = False) -> None:
        package_name = normalize_package_name(provider.package_name)
        if package_name in self._providers and not replace:
            raise ValueError(f"quiz package is already registered: {package_name}")
        self._providers[package_name] = provider

    def get(self, package_name: str) -> QuizPackageProvider:
        normalized = normalize_package_name(package_name)
        try:
            return self._providers[normalized]
        except KeyError as exc:
            raise KeyError(f"unknown quiz package: {normalized}") from exc

    def get_optional(self, package_name: str) -> QuizPackageProvider | None:
        try:
            normalized = normalize_package_name(package_name)
        except ValueError:
            return None
        return self._providers.get(normalized)

    def package_names(self) -> tuple[str, ...]:
        return tuple(self._providers)


quiz_package_registry = QuizPackageRegistry()
