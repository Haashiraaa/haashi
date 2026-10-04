# Releasing haashi

Releases are driven by git tags. Pushing a tag like `v1.2.0` does everything:

1. `changelog.yml` checks the tag is on `main` and CHANGELOG.md has a `## [1.2.0]` section.
2. `release.yml` checks the tag is on `main`, creates the GitHub Release from that
   changelog section, then dispatches `publish.yml`.
3. `publish.yml` builds the package, checks the built version equals the tag, and
   uploads to PyPI with Trusted Publishing (no API token stored anywhere).

`main` is protected: changes land through a pull request, and the `ci-ok` check
must pass before merging. Never push straight to `main`.

## Every release

```bash
git switch main && git pull
git switch -c release-1.2.0

# 1. Bump the version - the ONLY place it lives (keep it a plain string literal)
#    src/haashi/__init__.py:   __version__ = "1.2.0"

# 2. In CHANGELOG.md rename [Unreleased] contents into a new section:
#    ## [1.2.0] - YYYY-MM-DD - Short Title
#    and leave an empty  ## [Unreleased]  above it.

# 3. Verify locally
ruff check . && pyright && pytest
python -m build && twine check --strict dist/*

# 4. Push the release branch and open a PR into main
git add -A && git commit -m "Release 1.2.0"
git push -u origin release-1.2.0
#    GitHub -> Pull requests -> New pull request (base: main, compare: release-1.2.0)
#    Wait for the `ci-ok` check to go green, then merge.
#    (Squash or merge commit both work; the tag in step 5 goes on the result.)

# 5. Update local main to the merged result, then tag THAT commit and push the tag
git switch main && git pull
git tag -a v1.2.0 -m "haashi 1.2.0"
git push origin v1.2.0

# 6. Clean up
git branch -d release-1.2.0
```

Then watch **Actions** on GitHub: *Validate Changelog*, *Create Release*, *Publish to PyPI*.
If you enabled required reviewers on the `pypi` environment, approve the publish there.
Finally confirm from a clean environment:

```bash
python -m venv /tmp/check && /tmp/check/bin/pip install haashi==1.2.0
/tmp/check/bin/python -c "import haashi; print(haashi.__version__)"
```

## Rules to remember

- **A PyPI version can never be re-uploaded**, even after deleting it. If a release is
  wrong, fix forward with the next patch version (`1.2.1`).
- The tag must match `__version__` exactly (`v1.2.0` <-> `"1.2.0"`); `publish.yml` refuses otherwise.
- Tags must point at a commit that is on `main`. Always `git pull` on `main` after the
  merge and tag from there. Do not tag the release branch: squash merges create a new
  commit, so the branch commit is not on `main`.
- `main` only accepts changes through PRs. If you are on the ruleset bypass list you can
  push directly in an emergency, but prefer the PR flow.

## If something fails

| Symptom | Fix |
|---|---|
| PR can't merge, `ci-ok` is red | Fix the failure on the release branch, push again, and wait for green. |
| *Validate Changelog* fails | Add the `## [X.Y.Z]` section on a branch, merge it to `main` via PR, `git pull` on `main`, then move the tag: `git tag -d vX.Y.Z && git push origin :refs/tags/vX.Y.Z && git tag -a vX.Y.Z -m "..." && git push origin vX.Y.Z` |
| *Create Release* fails ("not on main") | You tagged a branch commit. Merge to `main` first, `git pull`, then re-tag from `main`. |
| *Publish* fails before uploading (version mismatch, build error) | Fix via a PR to `main`, then move the tag as above (nothing reached PyPI yet). |
| *Publish* fails with a trusted-publisher error | Check the publisher settings on PyPI (owner, repo, workflow `publish.yml`, environment `pypi`), then Actions -> *Publish to PyPI* -> **Run workflow** with the tag. |
| *Publish* says the file already exists | That version is already on PyPI. Bump to the next patch version. |
| `git push origin vX.Y.Z` is rejected | The `protect-release-tags` ruleset restricts `v*` tags. Make sure you are on its bypass list. |
