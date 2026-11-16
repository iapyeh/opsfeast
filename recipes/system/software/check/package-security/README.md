# OS package security workflow

This operation recipe powers the **OS package security meal** in the Recipes menu. It borrows the selected host session, collects a complete package snapshot, acquires matching vendor advisories on the controller and generates saved HTML/Markdown/JSON vulnerability reports. It does not patch packages.

Read [the end-to-end workflow](../../../../../docs/package-security-meal.md) for inputs, cache, authorization, failure states, native platform limits and report links.

Version 0.3.0 consumes inventory 0.2.0 with [native platform details](../../../../../docs/os-package-platforms.md). Vendor snapshots remain 0.1.0. FreeBSD VuXML/base SAs, Proxmox VE PSA and ESXi VMSA matching is available, with native branch and coverage limits.


Read [native vendor security](../../../../../docs/native-vendor-security.md) for automatic
source selection, explicit official URLs/imports and unsupported predicates.

*Last modified: 2026-11-13 23:25:46*
