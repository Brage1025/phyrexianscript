# Releasing

`pyproject.toml` is the toolchain version. `phyx.__version__` reads the installed distribution (`importlib.metadata.version("phyx")`). A checkout that is not installed reads `project.version` from `pyproject.toml` with `tomllib`. If neither works, the version is `0+unknown`.

An editable install keeps the metadata from the last install. After a bump, run `python -m pip install -e ".[dev]"` again before trusting `phyx --version` or `tests/test_versions.py`.

The language version is the first two numbers of the toolchain version (spec section 9). The specification heading names that language version, for example `(1.6)`, not the patch.

`editors/package.json` has its own cadence. Its `version` is an `X.Y.Z` and does not have to equal the toolchain version. Bump it only when the extension itself changed. `tests/test_versions.py` checks the shape, not equality with `pyproject.toml`.

## Steps

1. Merge the topic branch.
2. Bump every file that holds a number:
   - `pyproject.toml`: `project.version`.
   - `editors/package.json`: `version`, only if the extension changed. Keep it `X.Y.Z`.
   - `CHANGELOG.md`: rename `## Unreleased` to `## X.Y.Z - YYYY-MM-DD` and leave a new empty `## Unreleased` above it. The date is optional for the version test; the version in that heading must equal `project.version`, and `## Unreleased` must stay the first heading.
   - `docs/spec.md`: the heading's `(major.minor)`, only when the language version changed. A patch does not change it.
   - `README.md`: the Status line `Language version: X.Y`. `X.Y` is major.minor of `project.version`. A patch does not change it. The README does not hold the toolchain version; that number stays in `pyproject.toml` and on the PyPI badge. `tests/test_versions.py` fails when the line is missing or names a different major.minor.
3. Run `python -m pip install -e ".[dev]"` so the editable install picks up the new metadata.
4. Commit the bump.
5. Tag `vX.Y.Z` on that commit.
6. Create the GitHub release for that tag and publish it. Pushing the tag does not publish. The workflows below run on `release: types: [published]`. `workflow_dispatch` can run them without a release.

Do not create the tag or the release until the bump commit is the one you mean to ship.

## What the publish workflows do

Neither workflow reads a secret. Both authenticate with GitHub's OpenID Connect token (`permissions: id-token: write`). Neither job sets `environment:`.

### `publish.yml`

Runs when a release is published, and on `workflow_dispatch`. One job, `pypi`, on `ubuntu-latest`. It checks out the repository, installs Python 3.12, installs `build` and `twine`, runs `python -m build` and `python -m twine check dist/*`, then `pypa/gh-action-pypi-publish@release/v1` with no username, password, or repository URL. That action uploads the built distributions to PyPI using the job's OIDC token.

Configure this on the existing PyPI project, not as a GitHub secret. Open the project's Publishing page (`https://pypi.org/manage/project/phyx/settings/publishing/`, from Your projects → Manage `phyx` → Publishing). Add a GitHub Actions trusted publisher:

- Owner: `Brage1025`
- Repository name: `phyrexianscript`
- Workflow name: `publish.yml`
- Environment name: leave empty

PyPI's own docs recommend a GitHub environment. This workflow does not declare one, so a name on the PyPI form will not match the token and the upload will fail. Adding an environment means changing the workflow so the job's `environment:` is that same name. The workflow also does not run the tests before it uploads.

### `publish-extension.yml`

Runs when a release is published, and on `workflow_dispatch`. The dispatch input `registry` is `both` (the default), `marketplace`, or `openvsx`. On a published release the input is ignored and both jobs run, because each job's condition is true when `github.event_name == 'release'`. On a manual run, only the selected registry runs.

Both jobs run on `ubuntu-latest`, with `contents: read` and `id-token: write`, working directory `editors`, and Node 22. Each job packages with `npx --yes @vscode/vsce package --no-dependencies`.

The `marketplace` job uses `vsce publish --oidc` (`npx --yes @vscode/vsce publish --oidc --no-dependencies`). The workflow file contains no `VSCE_PAT` and no `--pat`, and there is nothing in GitHub secrets to fill in for this job. Whether the Marketplace accepts a trusted-publishing policy for this repository is unverified. Before relying on it for a release, run the "Publish extension" workflow manually (`workflow_dispatch`) with `registry=marketplace` and read the result. If it fails, the fix is a workflow change (a PAT secret or `--azure-credential`), not a docs change. The places to check are the [vsce README](https://github.com/microsoft/vscode-vsce/blob/main/README.md) and the VS Code [Publishing Extensions](https://code.visualstudio.com/api/working-with-extensions/publishing-extension) page.

The `openvsx` job runs `npx --yes ovsx publish --trusted-publishing --no-dependencies`. This workflow passes neither `--pat` nor `OVSX_PAT`.

Register the workflow under the namespace owner's Trusted Publishers settings, with the values below. The details of its rules should be read on the [Open VSX Trusted Publishing](https://github.com/eclipse-openvsx/openvsx/wiki/Trusted-Publishing) page, not copied here. Add GitHub Actions:

- Organization or user name: `Brage1025`
- Repository name: `phyrexianscript`
- Workflow filename: `publish-extension.yml`
- Environment name: leave empty

The job does not set `environment:`. A name in that field will not match.

A published release always runs this workflow, even when `editors/package.json` was not bumped. The registries reject a version that is already published, so that job fails. The workflow does not skip an unchanged extension version. That skip would be a workflow change.

## After it publishes

PyPI project page: `https://pypi.org/project/phyx/`. Then, in a new virtual environment outside this repository:

```
python -m venv phyx-check
phyx-check\Scripts\python -m pip install phyx==X.Y.Z
phyx-check\Scripts\phyx --version
```

On a Unix shell the executables are `phyx-check/bin/python` and `phyx-check/bin/phyx`. `--version` prints `φyrx X.Y.Z (PhyrxScript / PhyrexianScript)`.

Extension listings, version equal to `editors/package.json`:

- Visual Studio Marketplace: `https://marketplace.visualstudio.com/items?itemName=brage1025.phyx`
- Open VSX: `https://open-vsx.org/extension/brage1025/phyx`
