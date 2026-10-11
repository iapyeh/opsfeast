# Use, create and share recipes

A recipe is reusable operational content: code, purpose, prerequisites, inputs, results and verification instructions. You can use recipes supplied by Ops, ask your AI agent to build recipes for your environment, and share one recipe or a collection with others.

## What is available now

Start with the [recipe catalog](../recipes/README.md), then read the selected recipe's README. The catalog distinguishes availability, supported platforms and actual verification evidence.

Currently, only `inventory-system` and its dedicated runner are available. Other recipes can be authored, reviewed and shared, but a general runner, third-party installer, discovery service, lockfile and automatic signature verification are not implemented. Selecting a recipe directory in configuration does not mean the runner can execute it.

## Ask your AI agent to create a recipe

Start with the problem you want to solve; you do not need to learn the SSHScript API first. Describe the target platform, information or operation required, inputs, expected results and permitted side effects. Keep accounts, credentials and real host data in your management environment; do not paste passwords into chat.

Copy this prompt and replace the placeholders:

> I use SSHScript Ops at `/absolute/path/to/sshscript-ops`. Read README.md, AGENTS.md, docs/recipes.md and skills/sshscript-ops-recipes/SKILL.md. I need a recipe for [task] on Linux hosts, producing [fields and format]. Permitted operations are [for example, read-only queries without sudo or tool installation]. Use the public SSHScript skill and version-matched guides. Create the recipe in [my custom working directory], with synthetic examples, documentation and tests. Prepare a local draft and review first; do not connect, install dependencies, execute new code or publish. Report whether the current runner supports it and what authorization is needed next.

This prompt requests a draft first. You may include specific local test permissions if you want the agent to run them; already authorized steps do not require repeated approval. See the [authoring guide](recipe-authoring.md).

## Share your own recipes

Publish one or more recipes in your GitHub repository or deliver a ZIP/tar.gz archive. Include the license, usage instructions, compatibility, complete dependencies and synthetic examples. Exclude real hosts.yaml files, private keys, observations, logs and management directories. See the [sharing guide](recipe-sharing.md).

> Follow docs/recipe-sharing.md to prepare [explicit recipe directories] as [ZIP, tar.gz or a GitHub publication candidate]. Include only reviewed public files, with versions, a manifest, provenance, SHA-256 and verification evidence. Prepare a reviewable candidate first. Push only after the GitHub destination, visibility and publication scope are established and authorized. If I have already explicitly authorized publication to that destination, complete it within that scope.

## Use recipes shared by others

Have your agent acquire a candidate, verify its source and review its behavior before deciding whether to install. A README's safety claim, a successful download or a matching hash does not replace code review.

> Follow skills/sshscript-ops-recipes/SKILL.md and docs/recipe-acquisition.md to acquire [one or more specified recipes] from [repository URL and version, archive URL or local shared file] as candidates. Verify integrity and publisher evidence. Review local and remote side effects, credential access and dependencies, and prepare a pre-installation report. Do not execute candidates or tests, install dependencies or modify hosts.yaml. Install only after I authorize the concrete plan in the report. Installation does not include connection or execution.

## Documentation map

| Need | Guide |
| --- | --- |
| Available recipes and verification limits | [Recipe catalog](../recipes/README.md) |
| Ask an agent to create a custom recipe | [Authoring](recipe-authoring.md) |
| Share one recipe or a collection | [Sharing and packaging](recipe-sharing.md) |
| Acquire, verify, review and authorize installation | [Acquisition and installation](recipe-acquisition.md) |
| Knowledge and skills an agent should read | [Recipes skill](../skills/sshscript-ops-recipes/SKILL.md) |
| Keep knowledge and skills current | [Skill sources and updates](skill-updates.md) |

These guides describe human/agent workflows. Only explicitly documented existing tools are implemented features.
