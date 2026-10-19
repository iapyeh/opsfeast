# Recipe classification and location

Recipes use **domain → optional subdomains → action → recipe name**. There is no fixed two-level path or fixed subdomain depth. The filesystem path provides one canonical browsing location; the descriptor ID identifies the recipe independently of that location. This guide defines authoring conventions, not a newly enforced descriptor schema.

```text
recipes/
  system/
    account/check/identity/
    inventory/overview/
    network/check/port/
  feast/
    report/execution-summary/
    report/retention-summary/
```

Every recipe leaf contains recipe.yaml, its entrypoint, README.md, license and any required helpers/examples/schema. Intermediate classification directories are not recipes and do not contain recipe.yaml. Avoid putting another recipe below a recipe leaf: helpers, integrity digests and portable packaging belong to that individual leaf. Catalog and inspection recursively discover descriptors; explicit selectors resolve the complete path. Directory selection is immediate-child-only unless `recursive: true`; use recursive selection or an appropriate glob when selecting a domain tree. Always review the selected recipes before authorizing execution.

## Domains and boundaries

Use lowercase directory names and hyphens for multiword names. Add a subdomain when it improves discovery; do not create empty trees for capabilities that are not supplied.

| Domain | Scope | Illustrative future path |
| --- | --- | --- |
| system | Host hardware, accounts, processes, local storage and host-side networking | system/network/check/port |
| network | Network equipment and infrastructure control planes | network/router/check/bgp-neighbors |
| database | Database products and their own operations | database/mysql/backup/full |
| web | Web servers, reverse proxies and website services | web/nginx/check/configuration |
| middleware | Messaging, caches and application runtimes | middleware/rabbitmq/check/cluster |
| container | Container engines and orchestration | container/kubernetes/inventory/workloads |
| virtualization | Hypervisors and VM platforms | virtualization/vmware/esxi/inventory/datastores |
| cloud | Provider-specific resources and control planes | cloud/aws/ec2/inventory/instances |
| security | Cross-product vulnerability, certificate and compliance work | security/compliance/audit/host-baseline |
| observability | Monitoring, logging and tracing platforms | observability/prometheus/check/targets |
| backup | Backup platforms, repositories and restore verification | backup/restic/check/repository |
| feast | Feast's retained data, execution records and management work | feast/report/execution-summary |

Only the five recipes in the [bundle catalog](../recipes/README.md) are currently shipped. Other paths above are classification examples, not runnable or planned-delivery promises. Inventory overview spans several host domains and belongs under system/inventory. Host TCP reachability belongs under system/network; router configuration belongs under network. Product-specific backups belong with their product, while backup-platform operations belong under backup. Product-specific security checks/hardening stay with that product (for example database/mysql/audit/security-baseline); security contains work spanning products. Multi-OS implementations normally share one recipe rather than being copied into separate OS category trees.

## Actions

| Action | Meaning |
| --- | --- |
| inventory | Collect structured facts |
| check | Verify a concrete condition |
| audit | Assess against a policy or baseline |
| configure | Apply requested configuration |
| harden | Apply security-strengthening configuration |
| backup / restore | Save or restore data |
| maintain | Perform maintenance such as cleanup or rotation |
| report | Render existing data and explain evidence |

Actions classify purpose; access_mode, permissions, documented side effects and reviewed code determine actual authorization and privileges. An inventory/check/audit name does not prove read-only behavior. Classification does not install dependencies, select hosts, authorize execution or schedule work. There is no new tags/category/action descriptor field or category filter command in this change; use existing catalog query and source/path selectors.

## Where an agent creates a recipe

An agent normally creates a user's recipe at **`<selected-profile-root>/recipes/<classified-path>/`**. A profile is a registration pointing to an actual management directory; there is no required profiles/ parent. The default main profile commonly uses feasts/main/, so a local recipe might live at feasts/main/recipes/database/mysql/check/replication/. Do not modify bundled recipes to store user-specific operations.

| Source | Storage | Example selector |
| --- | --- | --- |
| Bundle | checkout recipes/ | system/network/check/port |
| Selected profile | profile-root recipes/ | :system/network/check/port |
| Registered shared repository | configured recipe_sources root | company:database/mysql/check/replication |

Use the [source guide](recipe-sources.md) for exact path/registration and selector rules. Profiles that share reviewed code should register a common external source rather than copy it repeatedly. Keep private bindings/credentials in runtime configuration, not in public portable code. Recipe creation, source registration, acquisition and execution remain separate authorization scopes.

## Bundled path relocation

The following directories have moved. Recipe IDs, recipe versions, execution/data contracts and collection semantics are unchanged.

| Previous bundle reference | Current bundle reference | Stable descriptor ID |
| --- | --- | --- |
| check/port | system/network/check/port | check-port |
| check/identity | system/account/check/identity | check-identity |
| inventory/system | system/inventory/overview | inventory-system |
| report/summary | feast/report/execution-summary | report-summary |
| report/retention | feast/report/retention-summary | report-retention |

Old bundle path selectors are removed; there are no aliases or automatic reference migrations. This move concerns bundled recipes only. User/profile/external repositories keep their own paths until their owners explicitly move them. New examples use the same convention for all sources; that does not relocate a user's existing copy.

For an existing environment, review and update hosts.yaml selectors, scripts, saved invocations/jobs, recipe_sources path assertions pointing inside the bundle, exact consumer subscriptions and report input filters. Root-level source assertions still point to recipes/ and need no relocation. Review saved jobs and recreate their invocation/content verification using the existing jobs save workflow when their source reference or packaged content has changed. Do not bypass digest checks or edit job verification files independently. See [saved jobs](recipe-experience.md#saved-jobs-and-recurring-work).

Historical raw results, retention envelopes, event journals and receipts keep their original recipe_reference and source paths. Do not rewrite that evidence to match current directories. Retention query filters are exact strings and can still select a historical reference even though that path is no longer executable. Offline retained-data reports can select both old and new references; broad source/contract subscriptions may span both. When changing an exact consumer subscription, decide whether to include the old reference for queued historical events or intentionally process only new events. Application rebuilds remain separate from event acknowledgement. No private configuration, job, consumer registration or historical record is modified automatically.

The inventory normalizer and retention schema are moved byte-for-byte so existing saved normalizer/schema digest bindings remain valid. The old path wording retained in their docstring/schema title is descriptive historical text, not an executable alias. Their contract remains inventory-observations 0.1.0. Shared schema references and the registered implementation location now point at system/inventory/overview. Replay uses the saved declaration and registered normalizer; explicit recipe-dir overrides use the new reviewed directory. Historical descriptor/result paths alone never cause remote collection.

## Verification and future moves

Use stable descriptor IDs across classification-only moves. Update product registries, public examples, consumers/report filters, shared schema references, skills and installed-package resources together. Rebase relative document/schema links and test deep source selection, symlink boundaries, static discovery, package contents, offline replay and preserved historical references. A future general move command is not implemented by this directory reorganization; use a separately reviewed change with explicit affected references and no automatic user-data rewrite.

_Last modified: 2026-10-19 15:24:36_
