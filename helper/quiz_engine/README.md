# Quiz package engine

Quiz content remains static for now, but application services access it through
`QuizPackageProvider`. This keeps content storage separate from quiz delivery,
progress, and report queue behavior.

## Current providers

`helper.quiz.quiz_data_extractor` registers the existing AG and SCL Python data
as `StaticQuizPackageProvider` instances. Their current immutable content version
is `legacy-v1`.

The compatibility functions in `quiz_data_extractor` keep the current API
payloads unchanged while delegating lookup to `quiz_package_registry`.

## Adding a static package

1. Define the full quiz list and the matching quiz-summary list.
2. Give every quiz and summary the same positive integer ID.
3. Register one `StaticQuizPackageProvider` during application bootstrap.
4. Add scoring and report handlers separately before enabling the package for
   users.
5. Add contract tests for quiz IDs, question IDs, payloads, scoring, and report
   output.

Use a new `definition_version` whenever published questions, choices, timing, or
scoring references change. Do not edit a published version in place.

## Future API source

An API-backed provider should implement `QuizPackageProvider` and be registered
under the same package name. Services should not know whether definitions came
from Python, JSON, a database, or an API. The provider must return one immutable
definition version and validate/cache remote content before making it active.

Scoring keys and private report rules must not be included in public quiz
payloads. Splitting those fields from the legacy AG/SCL definitions is a separate
migration because the current frontend payload contract must first be tested.
