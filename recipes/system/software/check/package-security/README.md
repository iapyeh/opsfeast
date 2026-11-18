# OS package security workflow

This operation recipe powers the **OS package security meal** in the Recipes menu. It borrows the selected host session, collects a complete package snapshot, acquires matching vendor advisories on the controller and generates saved HTML/Markdown/JSON vulnerability reports. It does not patch packages.

Read [the end-to-end workflow](../../../../../docs/package-security-meal.md) for inputs, cache, authorization, failure states, native platform limits and report links.

Version 0.3.0 consumes inventory 0.2.0 with [native platform details](../../../../../docs/os-package-platforms.md). Vendor snapshots remain 0.1.0. FreeBSD VuXML/base SAs, Proxmox VE PSA and ESXi VMSA matching is available, with native branch and coverage limits.


Read [native vendor security](../../../../../docs/native-vendor-security.md) for automatic
source selection, explicit official URLs/imports and unsupported predicates.

## Staged execution

Version 0.3.1 declares one Python `execute` stage under
[staged Recipe execution 0.1.0](../../../../../docs/staged-recipe-execution.md).
Normal CLI runs record one execution and river across the selected hosts.
Web plates retain their own shared execution, including grouped routine workers.
Recipe scope, permissions, result/retention schemas and native verification limits
are unchanged. Earlier saved results are preserved; no migration or replay occurs.

*Last modified: 2026-11-18 15:56:07*
