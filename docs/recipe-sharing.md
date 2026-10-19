# Share and package recipes

For inventory-observations 0.1.0 clones, include the recipe-local retention.schema.json in the explicit bundle allowlist and declare the required registered OpsFeast contract. A bundled normalizer file is not an automatically activated plugin: replay uses the installed reviewed contract implementation. New structured contracts need product registration, tests and guidance. Private retention/ and vault/ data are excluded from recipe bundles alongside observations/records/reports. See [creator-owned inventory retention](../recipes/system/inventory/overview/README.md#recipe-owned-retention-contract).


Share one recipe or several from a repository or archive. Complete the [authoring deliverables](recipe-authoring.md) first. This guide includes human/agent review procedures. The [recipes pack/unpack commands](recipe-experience.md#portable-recipe-bundles) implement explicit-file single-recipe bundles and verified candidates; publication, signing, dependency review and installation remain separate workflows.

Read [recipe attribution and installation defaults](recipe-attribution.md) for author name/contacts, declared license, Unknown placeholders and reserved Bundle policy. Before creating a user recipe, copy `python -B tools/recipe_identity.py defaults` into its descriptor. MIT pack allowlists include LICENSE; external unpack rejects Bundle before creating a candidate.

## Select content and publication scope

Confirm authorship, license, provenance and exact recipe versions. For multiple recipes, list each id, version, directory, dependencies and required shared files. A request to share one recipe does not include other private recipes.

Create a clean staging directory from an explicit file allowlist. Include code, README, recipe.yaml, synthetic examples, public tests, required assets and licenses. Exclude hosts.yaml, management locators, credentials, observations, logs, local agent guidance (AGENTS.local.md and AGENTS.override.md), venvs, caches, Git metadata and unnecessary hidden files. Inspect file contents; ignore rules cannot guarantee the absence of secrets. Preserve third-party licenses and provenance.

Suggested public layout, a sharing convention without an implemented collection schema or installer:

```text
my-recipes/
  README.md
  LICENSE
  MANIFEST.json
  recipes/
    inventory-example/...
    inspect-example/...
  shared/                 # Include only when needed
```

A single recipe can use one recipe subdirectory. The root README lists each recipe's purpose, version, entrypoint, compatibility and individual usage. Declare shared files as dependencies so selecting one recipe does not leave required content missing.

A suggested `MANIFEST.json` records bundle version, author, source URL/commit, recipe ids/versions/relative paths, dependencies and SHA-256 for every payload file. Describe the custom format and hash coverage in README. Exclude the manifest from its own digest list; an external archive signature covers the complete package. This is currently for review and manual comparison, not a format automatically understood by Ops. Parse it as data; never execute it.

## Share report recipes across Feasts

OpsFeast's community sharing direction includes report and visualization recipes; see [the shared principles](vision.md#accumulate-reusable-reports-and-keep-visualization-flexible) and [report authoring](recipe-authoring.md#report-recipes-and-reusable-visualization). Apply the same version, provenance, license, dependency and explicit-file selection workflow as for operational recipes.

Include reusable queries, transformations, interpretation rules, templates/assets, renderer requirements, input/output descriptions, documented invocation and synthetic test data. Parameterize source selection and output destinations so another Feast can bind its own compatible data without depending on the author's paths, hosts or agent platform. Explain actual input schema/version support, freshness/identity/partial-result handling and any external-service or model dependency. Preserve attribution for community contributions.

Exclude private source bindings, real operational datasets, credentials and generated reports by default. Sharing a report recipe does not authorize sharing the data it processes, publishing a dashboard or transmitting reports; those are separate explicit selections and scopes. Recipients review the complete candidate, choose local configuration and verify it using synthetic data before authorized operational use. Read [acquisition](recipe-acquisition.md) for the full process.

Git repositories or clean archives can carry these reviewed files today through the manual sharing workflow. Catalog discovery, offline python-report 0.1.0 execution/artifacts, pack/unpack bundles and saved reruns are implemented through [recipes commands](recipe-experience.md). Automatic installation/publication and a live OpsBuffet exchange remain unimplemented. Incompatible standalone scripts keep their reviewed invocation; registration does not adapt them to an implemented contract.

## ZIP or tar.gz

Package the clean staging directory with trusted tools. Use relative paths, ordinary files and directories; omit symlinks, hardlinks and special files. Inspect the archive listing, actual file set, size and unexpected content. Use a new filename rather than overwriting a previous release.

Record filename, byte size and SHA-256. Deliver the archive, README/manifest and verification evidence. For publisher authentication, use the user's configured signing tools to create a detached signature over the archive. Do not independently create, use or upload signing private keys. Provide the public-key fingerprint through a channel recipients can independently authenticate, rather than relying only on a key inside the download.

SHA-256 supports content comparison. To resist replacement of both the file and its digest, recipients need an independently trusted digest or a trusted publisher signature. See the [acquisition guide](recipe-acquisition.md).

## GitHub or another Git platform

Prepare a reviewable public candidate, then establish the user's account, repository, visibility, branch/tag and publication scope. For an existing repository, inspect the checkout, branch, remote and changes. Stage an explicit allowlist and review the staged diff; do not use `git add .` to include unrelated files.

Before making an existing repository public, inspect all history and accompanying data that will become public. Removing a current file does not remove secrets from history. If this cannot be established, prepare a clean publication candidate rather than exposing the original repository.

Commit, push or release within authorization. If publication is not authorized, first provide the file list, diff, verification evidence and destination plan, then obtain concrete publication authorization. Do not ask again for already explicitly authorized publication. Follow project rules for requested GitHub PRs; do not independently push to protected branches.

Record the actual commit, recipe subdirectories and release asset digests. Tags or commits may be signed using configured publisher keys. Tag names can move, so recipients record the resolved commit. Git signatures do not automatically authenticate separately uploaded ZIP assets; sign the release archive separately or authenticate its digest through signed data.

## Deliver skills and knowledge references

Recipe READMEs link to the [recipes skill](../skills/opsfeast-recipes/SKILL.md), [knowledge update guide](skill-updates.md) and public SSHScript entrypoint. When bundling a complete skill, preserve its license, provenance and references. The Ops recipes skill uses repository-relative links: standalone packaging must include linked guides and adjust paths, not just copy SKILL.md. Review third-party bundled skills using the [acquisition guide](recipe-acquisition.md) before installing them into an agent's instruction sources.

Report the actual package inventory, versions, digests, signature status, verification limits and delivery path. Report URLs/commits only after publication has actually occurred. Updates use new versions and describe changes; checking for updates and applying them are separate authorization scopes.

_Last modified: 2026-10-19 15:24:36_
