"""Registry for quiz package content providers."""

from helper.quiz_engine.contracts import QuizPackageProvider, QuizRuntimeProvider


def normalize_package_name(package_name: str) -> str:
    normalized = str(package_name or "").strip().upper()
    if not normalized:
        raise ValueError("package_name is required")
    return normalized


def normalize_version(version: str) -> str:
    normalized = str(version or "").strip()
    if not normalized:
        raise ValueError("version is required")
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


class QuizRuntimeRegistry:
    def __init__(self) -> None:
        self._providers: dict[tuple[str, str], QuizRuntimeProvider] = {}

    def register(self, provider: QuizRuntimeProvider, *, replace: bool = False) -> None:
        key = (
            normalize_package_name(provider.package_name),
            normalize_version(provider.scoring_version),
        )
        if key in self._providers and not replace:
            raise ValueError(
                f"quiz runtime is already registered: {key[0]}@{key[1]}"
            )
        self._providers[key] = provider

    def get(self, package_name: str, scoring_version: str) -> QuizRuntimeProvider:
        key = (
            normalize_package_name(package_name),
            normalize_version(scoring_version),
        )
        try:
            return self._providers[key]
        except KeyError as exc:
            raise KeyError(f"unknown quiz runtime: {key[0]}@{key[1]}") from exc

    def get_optional(
        self,
        package_name: str,
        scoring_version: str,
    ) -> QuizRuntimeProvider | None:
        try:
            key = (
                normalize_package_name(package_name),
                normalize_version(scoring_version),
            )
        except ValueError:
            return None
        return self._providers.get(key)

    def runtime_keys(self) -> tuple[tuple[str, str], ...]:
        return tuple(self._providers)


quiz_runtime_registry = QuizRuntimeRegistry()
