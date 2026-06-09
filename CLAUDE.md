# Claude Code project notes — realtime.docker_phpbb

Deploys [phpBB3](https://www.phpbb.com/) and MySQL as Docker Compose services
on a single Docker host. Traffic is routed via a Traefik reverse proxy managed
separately by `ansible-role-traefik`. The phpBB container image is built and
published by a dedicated image repository (`docker-phpbb`); this role only
pulls and runs it.

---

## Behavioral guidelines

These four rules govern how to work in this repo. They bias toward
caution over speed — for trivial one-liner changes, use judgment.

### 1. Think before writing tasks

**Don't assume. Surface tradeoffs. Ask when uncertain.**

Before adding or changing anything:

* State assumptions explicitly. If a variable could live in `defaults/`,
  `vars/`, or `host_vars`, say which and why before choosing.
* If multiple approaches exist (e.g. `ansible.builtin.command` vs a
  purpose-built module), present the tradeoff — don't pick silently.
* If the request is ambiguous (which task file? which template block?),
  name the ambiguity and ask. Don't guess and implement.
* If a simpler approach solves the problem, say so and push back.
* If something conflicts with `DESIGN.md`, flag it before proceeding.

### 2. Simplicity first

**Minimum tasks, variables, and template logic that solve the problem.**

* No new default variables beyond what the task being added requires.
* No Jinja2 abstraction for logic used in only one template.
* No `when:` conditions for scenarios that have no test coverage.
* No "future-proofing" of the public interface that wasn't asked for.
* If a template block is 30 lines and could be 10, rewrite it.

Ask: would a senior Ansible engineer call this overcomplicated? If yes,
simplify.

### 3. Surgical changes

**Touch only what the request requires. Clean up only your own mess.**

When editing existing tasks, templates, or defaults:

* Don't reformat adjacent YAML, fix unrelated comments, or clean up
  upstream code that wasn't broken by your change.
* Match the existing style — indentation, quoting, bullet character —
  even if you'd do it differently from scratch.
* If you notice unrelated dead code or stale variables, mention it;
  don't delete it without being asked.

When your change creates orphans:

* Remove `vars`, `when` conditions, or template blocks that YOUR change
  made unreachable.
* Don't remove pre-existing orphans unless explicitly asked.

Every changed line should trace directly to the request.

### 4. Goal-driven execution

**Define the success criteria before starting. Verify before declaring done.**

Transform requests into verifiable outcomes:

* "Add a preflight assertion" → `molecule converge` passes,
  `molecule verify` passes, `pre-commit run --all-files` is clean.
* "Fix an idempotency bug" → second `molecule converge` reports zero
  changed tasks.
* "Refactor a template" → rendered output is byte-for-byte identical
  to pre-refactor output on a converged instance.

For multi-step changes, state a brief plan before starting:

    1. Edit template → verify: rendered YAML is valid
    2. Add task       → verify: molecule converge green
    3. Add test       → verify: molecule verify green
    4. Lint           → verify: pre-commit run --all-files clean

Strong success criteria allow independent verification. Weak criteria
("make it work") require constant clarification.

---

## Role-specific notes

### Source of truth

`DESIGN.md` is the authoritative spec. Read it before any non-trivial
change. If code disagrees with `DESIGN.md`, `DESIGN.md` is right —
flag the discrepancy and ask before fixing the design to match the code.

### Design notes

`DESIGN.md` covers: purpose and non-goals, current state of the
hand-managed Docker Compose deployment and its pain points, architecture
decisions (container runtime, image strategy, network, secrets, logging,
MySQL initialisation, Traefik labels), full public interface variable
schema, Docker volume layout, task flow diagram, consumer-side notes
with host_vars examples, and open questions.

### Secrets

Role-specific secret variable names (vault on the consumer side; never
set in `defaults/`). The role templates these into
`{{ phpbb_compose_dir }}/.env.secrets` (0600, root-owned). Use
`no_log: true` on any task that touches them.

* `phpbb_mysql_root_password` — MySQL root password
* `phpbb_mysql_password` — MySQL password for the phpBB database user
* `phpbb_database_password` — phpBB application database password
  (must match `phpbb_mysql_password`)

### Commit scopes

Role-specific subsystem scopes: `mysql`, `phpbb`, `compose`, `network`,
`preflight`, `install`, `service`, `verify`

### Settled decisions

* Container runtime = Docker via `community.docker.docker_compose_v2`.
  No Swarm, no Kubernetes, no native systemd binary.
* phpBB image is pulled from a dedicated image repository
  (`basictheprogram/crossfire-phpbb3`). This role does not build images.
* Traefik is managed by `ansible-role-traefik`. This role assumes Traefik
  is already running and the Docker network exists.
* Docker network name defaults to `traefik_proxy` to match
  `ansible-role-traefik`'s `traefik_docker_network` default. Override
  via `phpbb_traefik_docker_network` if your Traefik deployment uses a
  different name.
* Secrets are vaulted in `host_vars/<host>/vault.yml` on the consumer
  side. This role never sets secret defaults.
* Logging driver = `journald`. The original Docker Compose project used
  syslog; journald is the standard for this role family.
* MySQL DB/user creation is handled by Docker's own init mechanism via
  environment variables (`MYSQL_DATABASE`, `MYSQL_USER`, etc.). No init
  SQL scripts are required for a fresh install.

### Open questions

If a task touches one of these, leave a `# TODO(open-q):` comment:

* Backup and restore from the existing Docker Compose deployment. The
  live named volumes (`phpbb_files`, `phpbb_images`, `phpbb_store`,
  `phpbb_ext`, `phpbb_config`, `phpbb-mysql-data`) contain production
  data. A migration runbook or role tasks for volume export/import have
  not yet been designed. (See TODO.md.)
* `remoteip.conf` in the phpBB image hard-codes `172.18.0.2` as the
  trusted Traefik proxy IP. This should either be parameterised in the
  image build or overridden at container runtime.
* phpBB image tag pinning strategy — whether to pin to a digest, a
  semver tag, or track `latest`.

### Implementation order

Work one section at a time. Each item = one focused session and one
commit. Stop and verify between items.

Items marked ✅ are complete and should not be re-opened unless a
specific regression or design change requires it.

1. ✅ Scaffold: copy config files, CLAUDE.md, meta/main.yml, README stub
2. `meta/main.yml` — namespace realtime, min_ansible_version 2.20,
   platforms (Ubuntu, Debian), galaxy metadata.
3. `defaults/main.yml` — public interface: image tags, container names,
   compose dir, network name, TZ, domain, logging, MySQL vars, phpBB vars.
4. `vars/main.yml` — empty fallback (no internal constants needed yet).
5. `templates/compose.yml.j2` — MySQL + phpBB services, named volumes,
   external Traefik network, journald logging, healthchecks, Traefik labels.
6. `templates/env.secrets.j2` — `.env.secrets` rendered from vault vars.
7. `tasks/preflight.yml` — assert required vars, Docker socket, network.
8. `tasks/install.yml` — create compose dir, render compose.yml and
   .env.secrets (mode 0600).
9. `tasks/network.yml` — assert `traefik_proxy` network exists (do not
   create it; owned by ansible-role-traefik).
10. `tasks/service.yml` — `community.docker.docker_compose_v2` up.
11. `tasks/verify.yml` — poll `docker inspect` until both containers healthy.
12. `tasks/main.yml` — orchestrates the above in order.
13. `handlers/main.yml` — `restart phpbb` and `restart mysql` handlers.
14. `molecule/default/` — platform matrix; testinfra verifier; self-contained
    fixtures; test suite covering rendered compose file, secrets file mode,
    and container health.
15. `.github/workflows/ci.yml` — GitHub Actions CI.
16. `DESIGN.md` — write after initial implementation is green.

### Consumer side notes

This role is consumed from a playbooks repo (not this repo). The consuming
host must have:

* Docker Engine installed and running.
* `ansible-role-traefik` applied first (creates the `traefik_proxy` network
  and starts Traefik).
* `host_vars/<host>/vault.yml` containing the three secret variables listed
  above, encrypted with `ansible-vault`.

Minimal `host_vars/<host>/phpbb.yml` example:

    phpbb_domain: forum.cross-fire.org
    phpbb_acme_email: techs@real-time.com
    phpbb_tz: America/Chicago
    phpbb_mysql_database: phpbb3
    phpbb_mysql_user: phpbb

---

## Conventions

* **Commits**: follow the commit message guide in this file exactly.
  Conventional Commits, imperative mood, bodies wrapped at 72,
  asterisk bullets.
* **Lint**: `.ansible-lint`, `.yamllint`, `.pre-commit-config.yaml`
  define the rules. Run `pre-commit run --all-files` before declaring
  work done.
* **Secrets**: never write a credential into a tracked file. Vault
  secrets are consumed on the consumer side; the role templates them
  into config files with restricted permissions. Use `no_log: true`
  on any task that touches them.
* **Modules**: prefer FQCNs (`ansible.builtin.template`, etc.).
  The `.ansible-lint` rules require it.
* **Idempotency**: every task should be safe to re-run.

## Testing locally

* `pre-commit run --all-files` — fast lint/format pass. Run before
  every commit.
* `molecule converge` then `molecule verify` — fast iteration during
  template / task work; skips the destroy/create cycle.
* `molecule test` — full role exercise per platform. Slow; run
  before declaring a change done.

## Test framework — testinfra

The verifier is **testinfra** (`pytest-testinfra`), not the Ansible
verifier. Tests are written in Python and live in:

    molecule/default/tests/test_default.py

Import `Host` from `testinfra.host` for type annotations, guarded by
`TYPE_CHECKING`:

    from __future__ import annotations
    from typing import TYPE_CHECKING
    if TYPE_CHECKING:
        from testinfra.host import Host

    def test_example(host: Host) -> None:
        assert host.file("/opt/phpbb").exists

All test functions must be annotated `host: Host` and return `-> None`.
Install dependencies: `pip install -r molecule/default/requirements.txt`.

## When in doubt

Read `DESIGN.md`, then ask. The schemas and decisions there are
load-bearing.

---

## Commit message guide

You are an expert DevOps engineer and professional git commit message
writer. When generating a commit message, follow these steps exactly.

### Step 1 — Retrieve changes

Run:

    git diff --cached

Analyze the full staged diff. This is the **single source of truth**
for what will be committed.

### Step 2 — Understand the change

Determine:

* The **primary purpose** of the change
* The **type of change** (feature, bug fix, refactor, etc.)
* The **most relevant scope** within the role
* Whether the change introduces a **breaking change** for role consumers
* Whether multiple changes should be summarized together

Pay special attention to:

* Changes to `defaults/main.yml` — these define the role's public interface
* Changes to handler names, task names, and tags — consumers may pin to them
* Changes to template variables that consumers override
* Changes to config or env file templates that affect service behavior
* Changes to `meta/main.yml` — galaxy metadata, min Ansible version, platforms

If multiple files are modified, identify the **dominant intent** rather
than listing every file.

### Step 3 — Select commit type

Use Conventional Commits:

* `feat` — new task, handler, variable, template, or capability
* `fix` — bug fix or idempotency correction
* `docs` — README, role metadata documentation, inline comments
* `style` — YAML formatting, whitespace, ansible-lint cleanup
* `refactor` — restructure tasks/templates without behavior change
* `perf` — performance improvement (e.g., reduced task runs, fewer handlers)
* `test` — molecule scenarios, lint config, CI tests
* `chore` — galaxy metadata, dependencies, tooling
* `ci` — GitHub Actions, GitLab CI, pre-commit hooks

### Step 4 — Determine scope

Infer a scope from the role layout or the subsystem being changed.

Common Ansible role scopes: `tasks`, `handlers`, `templates`,
`defaults`, `vars`, `meta`, `molecule`, `docker`.

Role-specific subsystem scopes: `mysql`, `phpbb`, `compose`, `network`,
`preflight`, `install`, `service`, `verify`

Only include a scope when it adds clarity. Prefer a subsystem scope
for feature-driven changes (e.g., `feat(mysql): ...`) and a role-layout
scope for structural changes (e.g., `refactor(tasks): ...`).

### Step 5 — Write the commit message

Format exactly as:

    <type>[optional scope]: <short summary (<=50 chars)>

    <body wrapped at 72 characters>

    [optional footer(s)]

**Subject line rules:**

* Use **imperative mood** ("Add", "Fix", "Update", "Remove")
* Maximum **50 characters**
* Describe the **result**, not the implementation
* Prefer role-specific or Ansible terminology over generic phrasing

**Body rules** (required):

Explain **why the change was made**, focusing on:

* What deployment scenario or upstream behavior motivated it
* What downstream role consumers need to know to upgrade safely
* Any Ansible version constraints involved

When helpful, summarize key changes using bullet points.

**Bullet rules:**

* Use `*` (asterisk) for all bullets — never `-` or `•`
* Nested bullets indented with two spaces
* No Markdown formatting of any kind

**Ansible role expectations:**

* Call out new, renamed, or removed default variables
* Note when handler names, tag names, or public task names change
* Mention idempotency improvements when relevant
* Reference supported platforms when adding OS-specific tasks
* Flag changes to `meta/main.yml` (min Ansible version, platforms)
* Note molecule scenario additions or removals

### Breaking changes

A change is breaking when it:

* Renames or removes a default variable
* Renames or removes a handler, tag, or public task name
* Changes a default value in a way that alters runtime behavior
* Drops support for an Ansible version or OS platform
* Restructures generated configuration in a way consumers' overrides
  cannot accommodate

If the diff introduces a breaking change:

* Add `!` after the type/scope in the subject
* Include a footer: `BREAKING CHANGE: <description>`

Examples:

    feat(mysql): add MySQL container with healthcheck
    feat(phpbb): add phpBB service with Traefik labels
    fix(compose): correct volume mount for config.php symlink
    refactor(tasks): split install and service into separate files
    chore(meta): bump minimum Ansible version to 2.20
    test(molecule): add scenario for Ubuntu 24.04

    feat(defaults)!: rename phpbb_db_password variable

    BREAKING CHANGE: phpbb_db_password is now phpbb_database_password;
    update host_vars vault before upgrading.

### Step 6 — Output rules

Return **only the commit message**. Do NOT include:

* explanations or analysis
* the diff
* markdown formatting
* code fences

The output must be a clean commit message ready for `git commit`.
It will be pasted directly into a git commit editor — optimize for
copy/paste fidelity over styling.
