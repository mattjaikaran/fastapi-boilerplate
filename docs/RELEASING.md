# Releasing

This project uses [Semantic Versioning](https://semver.org/spec/v2.0.0.html). The version in `pyproject.toml` (`[project].version`) is the single source of truth. `settings.APP_VERSION` reads it at run time, so you never edit the version anywhere else.

## Prerequisites

- You have push access to `main` and to tags.
- You have `uv` and `git` installed.
- The CI workflow passes on `main`.

## Release steps

1. Update `main`:

   ```bash
   git checkout main
   git pull --ff-only
   ```

2. Bump the version. Choose the part that matches your changes:

   ```bash
   make bump-patch   # bug fixes only
   make bump-minor   # backward-compatible features
   make bump-major   # breaking changes
   make version      # confirm the new version
   ```

3. Update `CHANGELOG.md`:
   - Rename the `## [Unreleased]` entries into a new `## [X.Y.Z] - YYYY-MM-DD` section.
   - Leave an empty `## [Unreleased]` section above it.
   - Update the link references at the bottom of the file.

4. Commit the bump and the changelog:

   ```bash
   git add pyproject.toml uv.lock CHANGELOG.md
   git commit -m "chore(release): vX.Y.Z"
   git push origin main
   ```

5. Create and push the tag:

   ```bash
   make release
   ```

   The target stops if the working tree is dirty, you are not on `main`, `CHANGELOG.md` has no section for the version, or the tag exists. Otherwise it creates the annotated tag `vX.Y.Z` and pushes it.

6. Watch the **Release** workflow in GitHub Actions. For a tag that matches `v*.*.*`, it:
   1. Checks that the tag equals the `pyproject.toml` version.
   2. Runs lint, type check, and tests.
   3. Builds the sdist and wheel with `uv build`.
   4. Copies the matching `CHANGELOG.md` section into the release notes.
   5. Creates the GitHub release and attaches the files in `dist/`.

## Pre-releases

Use a PEP 440 version, for example `0.2.0rc1`, and tag it `v0.2.0rc1`. The workflow marks any release whose version contains a letter or hyphen as a pre-release. Add a matching `## [0.2.0rc1]` section to `CHANGELOG.md`.

## Fix a failed release

- If the tag and version do not match, delete the remote tag, fix `pyproject.toml`, and run `make release` again:

  ```bash
  git push origin --delete vX.Y.Z
  git tag -d vX.Y.Z
  ```

- If a test fails, fix it on `main`, then move the tag with the same delete commands before you run `make release`.
