# Complete OS package database snapshot

Collector 0.2.0 supports Linux dpkg/RPM, Proxmox VE product/component identity, FreeBSD pkg plus base/kernel patch versions, and ESXi native VIB/component XML without target Python. Fingerprints and final rereads preserve explicit partial states.

See [native platform commands, fields and limits](../../../../../docs/os-package-platforms.md). Older 0.1.0 snapshots require recollection for current assessment; existing evidence is not migrated or deleted. Not an application/container SBOM.

Read the [package-security workflow](../../../../../docs/os-package-security.md) for inputs, authorization, versioned contracts, source provenance and platform/verification limits.

## Staged execution

Version 0.2.1 declares one Python `collect` stage under
[staged Recipe execution 0.1.0](../../../../../docs/staged-recipe-execution.md).
Normal CLI runs record one execution and river across the selected hosts.
Web plates retain their own shared execution, including grouped routine workers.
Recipe scope, permissions, result/retention schemas and native verification limits
are unchanged. Earlier saved results are preserved; no migration or replay occurs.

*Last modified: 2026-11-18 15:56:07*
