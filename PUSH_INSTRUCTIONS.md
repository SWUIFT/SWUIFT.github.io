# Fresh push + v1.0.0 release instructions

This directory (`SWUIFT-PUBLIC-RELEASE`) is a clean copy of the public tree at
**package version 1.0.0**, with `origin` set to:

`https://github.com/SWUIFT/SWUIFT.github.io.git`

Download digests in the docs are `REPLACE_AFTER_BUILD` until you publish assets.

`SWUIFT-PUBLIC` is untouched.

---

## 0. Prerequisites

- GitHub auth that can **admin** `SWUIFT/SWUIFT.github.io` (org owner/admin).
- `gh` CLI logged in (`gh auth login`), or use the GitHub web UI where noted.
- Repo secrets still configured for desktop signing if you want signed installers
  (Apple/Windows cert secrets used by `.github/workflows/build-desktop.yml`).

---

## 1. Wipe the existing GitHub repo (history, tags, releases)

**Destructive.** This replaces the remote with a brand-new history.

### A. Delete all releases and tags on GitHub

```bash
cd /home/csgrad/utkarshk/doe_code_verify/SWUIFT-PUBLIC-RELEASE

# Delete every release (assets go with them)
gh release list --repo SWUIFT/SWUIFT.github.io --limit 100 \
  | awk -F'\t' '{print $3}' \
  | while read -r tag; do
      [ -n "$tag" ] && gh release delete "$tag" --repo SWUIFT/SWUIFT.github.io --yes
    done

# Delete every tag on the remote
git ls-remote --tags origin \
  | awk '{print $2}' \
  | sed 's#refs/tags/##' \
  | sed 's/\^{}//' \
  | sort -u \
  | while read -r tag; do
      git push origin ":refs/tags/$tag"
    done
```

### B. Force-push this fresh `main` (replaces all commits)

A local commit already exists in this folder. Review, then:

```bash
cd /home/csgrad/utkarshk/doe_code_verify/SWUIFT-PUBLIC-RELEASE
git remote -v   # must show SWUIFT/SWUIFT.github.io.git
git log -1 --oneline

# THIS REWRITES origin/main
git push --force origin main
```

Optional: in GitHub → **Settings → Pages**, confirm source is **GitHub Actions**
(the `docs.yml` MkDocs workflow), not a stale `gh-pages` branch.

---

## 2. Confirm site build

After the force-push, wait for the **Docs** / Pages workflow:

```bash
gh run list --repo SWUIFT/SWUIFT.github.io --workflow docs.yml --limit 5
```

Site: https://swuift.github.io/

---

## 3. Build and publish **v1.0.0** assets (fresh)

### A. Tag and push (triggers release + desktop workflows)

```bash
cd /home/csgrad/utkarshk/doe_code_verify/SWUIFT-PUBLIC-RELEASE

# Confirm packages are 1.0.0
python3 scripts/check_release_metadata.py --tag v1.0.0

git tag -a v1.0.0 -m "SWUIFT v1.0.0"
git push origin v1.0.0
```

That should start:

- `.github/workflows/release.yml` → wheels, sdists, `SHA256SUMS`, GitHub Release
- `.github/workflows/build-desktop.yml` → Windows `.exe` + macOS `.dmg` (if runners/secrets OK)

Watch:

```bash
gh run list --repo SWUIFT/SWUIFT.github.io --limit 10
gh release view v1.0.0 --repo SWUIFT/SWUIFT.github.io
```

### B. Attach Marshall archives to the same release

Package (needs local Marshall data / validated outputs as documented by the scripts):

```bash
# Inputs archive (see script --help for paths)
python3 scripts/package_marshall_example.py

# Outputs archive
python3 scripts/package_marshall_output.py
```

Upload without replacing unrelated assets:

```bash
gh release upload v1.0.0 \
  examples/artifacts/marshall_20211230_1100-2100_MST-inputs.tar.gz \
  examples/artifacts/marshall_20211230_1100-2100_MST-output.tar.gz \
  --repo SWUIFT/SWUIFT.github.io \
  --clobber   # only if re-uploading the same Marshall filenames
```

Omit `--clobber` on first upload.

### C. Fill digests in docs (second commit)

```bash
# Example: hash published assets
for f in \
  SWUIFT_Setup_1.0.0.exe \
  SWUIFT_macOS_arm64.dmg \
  SWUIFT_macOS_x86_64.dmg \
  marshall_20211230_1100-2100_MST-inputs.tar.gz \
  marshall_20211230_1100-2100_MST-output.tar.gz
do
  curl -sSL "https://github.com/SWUIFT/SWUIFT.github.io/releases/download/v1.0.0/$f" \
    | sha256sum | awk -v f="$f" '{print $1, f}'
done

git rev-parse --short v1.0.0   # use for Tagged commit in downloads.md
```

Replace every `REPLACE_AFTER_BUILD` and `REPLACE_AFTER_TAG` in:

- `docs/downloads.md`
- `docs/installation.md`
- `docs/marshall-tutorial.md`
- `examples/marshall_20211230_1100-2100_MST/README.md`

Then:

```bash
git add docs examples
git commit -m "$(cat <<'EOF'
Record v1.0.0 release digests and tagged commit

EOF
)"
git push origin main
```

Do **not** retag or rebuild assets for that docs-only commit unless you intend a new version.

---

## 4. Sanity checks

```bash
# Assets reachable
for f in SWUIFT_Setup_1.0.0.exe SWUIFT_macOS_arm64.dmg SWUIFT_macOS_x86_64.dmg \
         SHA256SUMS \
         marshall_20211230_1100-2100_MST-inputs.tar.gz \
         marshall_20211230_1100-2100_MST-output.tar.gz; do
  curl -sSIL -o /dev/null -w "%{http_code} $f\n" \
    "https://github.com/SWUIFT/SWUIFT.github.io/releases/download/v1.0.0/$f"
done

# Metadata still matches tag
python3 scripts/check_release_metadata.py --tag v1.0.0
```

---

## Notes

- Force-push does **not** by itself delete releases; step 1A does.
- Old personal repo `utkrshkmr/SWUIFT` is unrelated after this cutover.
- Keep developing in `SWUIFT-PUBLIC` if you want; this folder is the release cut.
