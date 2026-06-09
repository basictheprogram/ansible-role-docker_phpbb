# TODO — ansible-role-docker_phpbb

## Session: ansible-sync-role pass (2026-06-08)

All 14 sync steps clean against correct role path. No changes required
beyond the trailing newline fix in `tasks/preflight.yml`.

---

## Session: initial scaffold + DESIGN.md (2026-06-08)

### Completed this session

* Synced config files from `_template/`: `.ansible-lint`, `.gitignore`,
  `.pre-commit-config.yaml`, `.yamllint`, `ruff.toml`
* Generated `CLAUDE.md` with role-specific placeholders filled
* Created `meta/main.yml` — namespace `realtime`, min Ansible 2.20,
  Ubuntu (jammy/noble/resolute) and Debian (bookworm/trixie) platforms
* Created `defaults/main.yml` — full public interface for MySQL + phpBB
* Created `vars/main.yml` — empty fallback (no internal constants yet)
* Created `templates/compose.yml.j2` — MySQL + phpBB services, named
  volumes, external Traefik network, journald logging, healthchecks,
  Traefik labels
* Created `templates/env.secrets.j2` — `.env.secrets` from vault vars
* Created `tasks/preflight.yml` — Ansible version, required vars,
  Docker socket, Traefik network existence
* Created `tasks/install.yml` — compose dir, compose.yml, .env.secrets
* Created `tasks/service.yml` — `docker_compose_v2` bring-up
* Created `tasks/verify.yml` — healthcheck polling for both containers
* Created `tasks/main.yml` — orchestration
* Created `handlers/main.yml` — restart phpbb, restart mysql
* Created `README.md`
* Created `molecule/default/` scaffold — platform matrix, testinfra
  verifier, self-contained group_vars fixtures, test suite
* Created `DESIGN.md` — architecture decisions, public interface schema,
  volume layout, task flow, consumer side notes, open questions

---

### Open items

* [ ] Add `.github/workflows/ci.yml` — GitHub Actions CI matching the
  traefik role's pattern.
* [ ] Verify `community.docker.docker_network_info` is the correct
  module for asserting network existence in preflight (check collection
  docs; module name may differ from `docker_network_info`).
* [ ] Pin `phpbb_image` to a specific semver tag once the dedicated
  image repo has a release pipeline. `latest` is acceptable for initial
  bring-up only.
* [ ] Run `pre-commit run --all-files` and fix any lint violations.
* [ ] Run `molecule converge && molecule verify` against at least one
  platform and fix failures.
* [ ] Add `meta/argument_specs.yml` documenting every key in
  `defaults/main.yml` once the interface stabilises.

---

### Future work

* [ ] **Backup and restore from existing Docker Compose deployment.**
  The live named volumes (`phpbb_files`, `phpbb_images`, `phpbb_store`,
  `phpbb_ext`, `phpbb_config`, `phpbb-mysql-data`) contain production
  data. Design a migration runbook or role tasks for:
  1. Exporting volumes from the existing Docker Compose host
  2. Importing into the Ansible-managed deployment
  This should be a separate session and commit once the role is proven
  on a fresh deployment.

* [ ] **`remoteip.conf` Traefik IP.** The phpBB image hard-codes
  `172.18.0.2` as the trusted Traefik proxy IP. This will silently pass
  the wrong client IP to phpBB if the Docker network assigns a different
  address. Fix options: parameterise via build arg in the image repo, or
  override at container runtime via env var and entrypoint logic.

* [ ] **Dedicated phpBB image repo.** The image
  `basictheprogram/crossfire-phpbb3` needs its own GitHub repo with a
  release pipeline (GitHub Actions, semver tags, Docker Hub push). The
  `remoteip.conf` IP issue should be resolved there.

* [ ] **Molecule scenario: preflight failure cases** — bad/empty
  required vars, missing Docker network.

* [ ] **Molecule scenario: deeper compose verification** — parse
  rendered `compose.yml` as YAML and assert structure rather than
  string-matching content.
