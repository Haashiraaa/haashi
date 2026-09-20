# Releasing haashi

Releases are driven by git tags. Pushing a tag like `v1.2.0` does everything:

1. `changelog.yml` checks the tag is on `main` and CHANGELOG.md has a `## [1.2.0]` section.
2. `release.yml` checks the tag is on `main`, creates the GitHub Release from that
   changelog section, then dispatches `publish.yml`.
3. `publish.yml` builds the package, checks the built version equals the tag, and
   uploads to PyPI with Trusted Publishing (no API token stored anywhere).

## Every release

```bash
git switch main && git pull

# 1. Bump the version - the ONLY place it lives (keep it a plain string literal)
#    src/haashi/__init__.py:   __version__ = "1.2.0"

# 2. In CHANGELOG.md rename [Unreleased] contents into a new section:
#    ## [1.2.0] - YYYY-MM-DD - Short Title
#    and leave an empty  ## [Unreleased]  above it.

# 3. Verify locally
ruff check . && pyright && pytest
python -m build && twine check --strict dist/*

# 4. Ship it to main and wait for the CI run to go green
git add -A && git commit -m "Release 1.2.0" && git push

# 5. Tag and push the tag
git tag -a v1.2.0 -m "haashi 1.2.0"
git push origin v1.2.0
```

Then watch **Actions** on GitHub: *Validate Changelog*, *Create Release*, *Publish to PyPI*.
Finally confirm from a clean environment:

```bash
python -m venv /tmp/check && /tmp/check/bin/pip install haashi==1.2.0
/tmp/check/bin/python -c "import haashi; print(haashi.__version__)"
```

## Rules to remember

- **A PyPI version can never be re-uploaded**, even after deleting it. If a release is
  wrong, fix forward with the next patch version (`1.2.1`).
- The tag must match `__version__` exactly (`v1.2.0` <-> `"1.2.0"`); `publish.yml` refuses otherwise.
- Tags must point at a commit that is on `main`.

## If something fails

| Symptom | Fix |
|---|---|
| *Validate Changelog* fails | Add the `## [X.Y.Z]` section, commit to `main`, then move the tag: `git tag -d vX.Y.Z && git push origin :refs/tags/vX.Y.Z && git tag -a vX.Y.Z -m "..." && git push origin vX.Y.Z` |
| *Create Release* fails ("not on main") | You tagged a branch commit. Merge to `main` first, then re-tag. |
| *Publish* fails before uploading (version mismatch, build error) | Fix on `main`, move the tag as above (nothing reached PyPI yet). |
| *Publish* fails with a trusted-publisher error | Check the publisher settings on PyPI (owner, repo, workflow `publish.yml`, environment `pypi`), then Actions -> *Publish to PyPI* -> **Run workflow** with the tag. |
| *Publish* says the file already exists | That version is already on PyPI. Bump to the next patch version. |
