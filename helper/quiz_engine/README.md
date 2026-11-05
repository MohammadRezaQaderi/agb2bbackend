# Quiz package engine

Quiz content remains static for now, but application services access it through
`QuizPackageProvider`. This keeps content storage separate from quiz delivery,
progress, and report queue behavior.

## Current providers

`helper.quiz.quiz_data_extractor` registers the existing AG and SCL Python data
from `quiz_packages/<package>/legacy_v1` as `StaticQuizPackageProvider`
instances. Their current immutable content version is `legacy-v1`.

Each version folder owns its question definitions, private scoring schema, and
static report rules. The modules under `helper.quiz` remain compatibility imports
for older callers and should not receive new package content.

The compatibility functions in `quiz_data_extractor` preserve the public quiz
shape while delegating lookup to `quiz_package_registry`; private fields are the
only intentional omission.

`get_quiz_info` returns a fresh public copy and removes private question fields
such as `question_answer`. Trusted backend code that genuinely requires the
complete definition must use `get_private_quiz_info` explicitly.

## Adding a static package

1. Define the full quiz list and the matching quiz-summary list.
2. Give every quiz and summary the same positive integer ID.
3. Add a version-folder `create_provider` factory and include it in
   `quiz_packages.builtin.BUILTIN_PACKAGE_FACTORIES`.
4. Add scoring and report handlers separately before enabling the package for
   users.
5. Add contract tests for quiz IDs, question IDs, payloads, scoring, and report
   output.

Use a new `definition_version` whenever published questions, choices, timing, or
scoring references change. Do not edit a published version in place.

Every new `quiz_attempt` stores both `definition_version` and
`scoring_version`. Updating an attempt must preserve its original versions so a
future scorer can reproduce the result that belonged to that attempt.

## Future API source

An API-backed provider should implement `QuizPackageProvider` and be registered
under the same package name. Services should not know whether definitions came
from Python, JSON, a database, or an API. The provider must return one immutable
definition version and validate/cache remote content before making it active.

Scoring keys and private report rules must not be included in public quiz
payloads. Legacy `question_answer` fields remain in the private source for
compatibility but are removed by the public provider boundary.

## Regression baseline

`tests/fixtures/quiz_regression/legacy_v1.json` records the published AG/SCL
definition, scoring, and static report behavior. The snapshot test fingerprints
semantic objects and representative scoring outputs, so formatting-only changes
to the large data modules do not invalidate it.

When quiz behavior intentionally changes, publish a new definition/scoring
version and create a new reviewed fixture. Do not overwrite the `legacy-v1`
baseline to make an unexpected test failure pass.
