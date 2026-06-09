# ansible-role-docker_phpbb — Design

## Purpose

Deploy phpBB3 and MySQL as Docker Compose services on a single Docker host,
managed by Ansible rather than a hand-maintained `compose.yml` and `.env`
file. Replaces a manually operated Docker Compose project
(`forums.cross-fire.org`) that mixed application source, image build,
Traefik configuration, and service runtime into one repository.

## Goals

* One Ansible role manages MySQL and phpBB containers. A single `host_vars`
  file describes the deployment; no hand-editing of compose files on the
  target host.
* Secrets live in `ansible-vault`-encrypted `host_vars/<host>/vault.yml`.
  No credentials are stored in plaintext in any tracked file.
* The role integrates cleanly with [`ansible-role-traefik`](https://github.com/basictheprogram/ansible-role-traefik): it attaches to
  the Docker network that role creates and emits the Traefik labels that
  role reads. No Traefik configuration lives in this role.
* The phpBB container image is built and published by a dedicated image
  repository (`docker-phpbb`). This role only pulls and runs it.
* Compatible with `ansible-core` >= 2.20, Debian 12/13 and Ubuntu
  22.04/24.04/26.04.

## Non-goals

* No image build. The role does not build, tag, or push the phpBB image.
* No Traefik management. The role assumes Traefik is already running and
  the Docker network already exists.
* No DNS record automation. The operator is responsible for pointing the
  domain at the host.
* No host-level firewall management.
* No backup or restore tasks (future work — see TODO.md).

---

## Current state (reference: hand-managed deployment)

The live deployment runs on a single VM:

```
forums.cross-fire.org/
├── compose.yml          # MySQL + phpBB services
├── .env                 # all config and secrets in plaintext
├── php/
│   ├── Dockerfile       # custom phpBB image build
│   ├── docker-entrypoint.sh
│   └── remoteip.conf    # Apache trusted proxy IP (hard-coded)
└── traefik/
    ├── compose.yml      # Traefik service
    └── config/
        └── traefik.yml  # static Traefik config
```

Pain points in the hand-managed deployment:

* Secrets (`MYSQL_ROOT_PASSWORD`, `MYSQL_PASSWORD`, `PHPBB_DATABASE_PASSWORD`)
  stored in plaintext in `.env`, committed to the repository.
* Image build, runtime config, and Traefik config all co-located in one repo.
* Logging driver is `syslog` pointing at a remote rsyslog server; journald
  is the standard for this role family and is better suited to systemd hosts.
* `remoteip.conf` hard-codes `172.18.0.2` as the trusted Traefik proxy IP;
  this will silently break if the Docker network assigns a different address.
* No Ansible management; deployment requires manual SSH and `docker compose`
  commands.

---

## Architecture decisions

### Container runtime

`community.docker.docker_compose_v2` manages both containers from a single
`compose.yml` rendered by Ansible. No Swarm, no Kubernetes, no native systemd
binary for the containers themselves.

### Image strategy

The phpBB container image is pulled from Docker Hub:
`basictheprogram/crossfire-phpbb3`. This role does not build images. The image
is maintained in a separate repository with its own release pipeline (GitHub
Actions, semver tags). The role defaults to `latest` for initial bring-up; pin
to a digest or semver tag in `host_vars` once the image pipeline is stable.

### Network

[`ansible-role-traefik`](https://github.com/basictheprogram/ansible-role-traefik) creates and owns the `traefik_proxy` Docker network.
This role only attaches to it. The network name is configurable via
`phpbb_traefik_docker_network` (default: `traefik_proxy`) to match
`traefik_docker_network` in `ansible-role-traefik`. Preflight asserts the
network exists before proceeding.

### Secrets

All three passwords are vaulted on the consumer side in
`host_vars/<host>/vault.yml`. The role templates them into
`{{ phpbb_compose_dir }}/.env.secrets` (mode 0600, root-owned) and passes
that file to Docker Compose via `env_file:`. The role never sets these
variables in `defaults/main.yml` and uses `no_log: true` on every task that
references them.

### Logging

Both containers use the `journald` logging driver. The original Docker Compose
project used `syslog` pointing at a remote rsyslog server; journald is the
standard for this role family and is native to systemd-based hosts. The
journald tag is configurable per container via `phpbb_journald_tag_phpbb` and
`phpbb_journald_tag_mysql`.

### MySQL initialisation

MySQL DB and user creation is handled by the MySQL Docker image's own init
mechanism via environment variables (`MYSQL_DATABASE`, `MYSQL_USER`,
`MYSQL_PASSWORD`, `MYSQL_ROOT_PASSWORD`). No init SQL scripts are needed for
a fresh install. The role does not ship SQL files or use the
`docker-entrypoint-initdb.d` mechanism.

### Traefik labels

The phpBB container emits the following Traefik labels, all parameterised:

```
traefik.enable=true
traefik.http.routers.phpbb3.rule=Host(`{{ phpbb_domain }}`)
traefik.http.routers.phpbb3.entrypoints={{ phpbb_traefik_entrypoint }}
traefik.http.routers.phpbb3.tls=true
traefik.http.routers.phpbb3.tls.certresolver={{ phpbb_traefik_certresolver }}
traefik.http.services.phpbb3.loadbalancer.server.port=80
```

MySQL has `traefik.enable=false`.

---

## Public interface (defaults/main.yml)

### Image and runtime

| Variable | Default | Notes |
|---|---|---|
| `phpbb_image` | `basictheprogram/crossfire-phpbb3:latest` | Pin to semver in production |
| `phpbb_container_name` | `phpbb` | |
| `phpbb_restart_policy` | `unless-stopped` | |
| `phpbb_mysql_image` | `mysql:lts` | |
| `phpbb_mysql_container_name` | `phpbb-mysql` | |
| `phpbb_mysql_restart_policy` | `unless-stopped` | |

### Filesystem

| Variable | Default | Notes |
|---|---|---|
| `phpbb_compose_dir` | `/opt/phpbb` | Holds `compose.yml` and `.env.secrets` |

### Networking

| Variable | Default | Notes |
|---|---|---|
| `phpbb_traefik_docker_network` | `traefik_proxy` | Must match `traefik_docker_network` in [`ansible-role-traefik`](https://github.com/basictheprogram/ansible-role-traefik) |

### Runtime

| Variable | Default | Notes |
|---|---|---|
| `phpbb_tz` | `UTC` | Timezone for both containers |
| `phpbb_domain` | `""` | **Required.** FQDN (e.g. `forum.example.com`) |
| `phpbb_apache_server_admin` | `webmaster@localhost` | |
| `phpbb_traefik_entrypoint` | `websecure` | |
| `phpbb_traefik_certresolver` | `letsencrypt` | |

### Logging

| Variable | Default | Notes |
|---|---|---|
| `phpbb_compose_log_driver` | `journald` | |
| `phpbb_journald_tag_phpbb` | `phpbb.{{ inventory_hostname }}` | |
| `phpbb_journald_tag_mysql` | `phpbb-mysql.{{ inventory_hostname }}` | |

### MySQL (non-secret)

| Variable | Default | Notes |
|---|---|---|
| `phpbb_mysql_database` | `phpbb3` | |
| `phpbb_mysql_user` | `phpbb` | |
| `phpbb_mysql_host_port` | `3306` | |

### phpBB (non-secret, derived)

| Variable | Default | Notes |
|---|---|---|
| `phpbb_database_host` | `{{ phpbb_mysql_container_name }}` | |
| `phpbb_database_port` | `{{ phpbb_mysql_host_port }}` | |
| `phpbb_database_name` | `{{ phpbb_mysql_database }}` | |
| `phpbb_database_user` | `{{ phpbb_mysql_user }}` | |

### Secrets (must be vaulted; empty defaults are intentional)

| Variable | Notes |
|---|---|
| `phpbb_mysql_root_password` | MySQL root password |
| `phpbb_mysql_password` | MySQL password for the phpBB user |
| `phpbb_database_password` | phpBB application DB password (must match `phpbb_mysql_password`) |

### Verification

| Variable | Default | Notes |
|---|---|---|
| `phpbb_verify_healthcheck` | `true` | Poll containers until healthy |
| `phpbb_verify_healthcheck_retries` | `10` | |
| `phpbb_verify_healthcheck_delay` | `15` | Seconds between retries |

---

## Volume layout

All volumes are named Docker volumes managed by Docker Compose. The role
does not manage volume lifecycle beyond what `docker_compose_v2` handles.

| Volume | Mounted at | Contents |
|---|---|---|
| `phpbb-mysql-data` | `/var/lib/mysql` | MySQL data directory |
| `phpbb_config` | `/config-volume` | `config.php` (persisted across restarts via entrypoint symlink) |
| `phpbb_files` | `…/phpBB3/files` | User-uploaded attachments |
| `phpbb_images` | `…/phpBB3/images` | Custom images and avatars |
| `phpbb_store` | `…/phpBB3/store` | Cache and backups |
| `phpbb_ext` | `…/phpBB3/ext` | phpBB extensions |

The `phpbb_config` volume preserves `config.php` across container restarts.
The phpBB image's entrypoint symlinks `/var/www/html/phpBB3/config.php` →
`/config-volume/config.php` on every start. If `config.php` is non-empty the
entrypoint also removes the phpBB install directory, preventing re-installation
on restart.

---

## Task flow

```
preflight.yml
  ├── assert Ansible >= 2.20
  ├── assert phpbb_domain is set
  ├── assert secrets are non-empty (no_log: true)
  ├── assert /var/run/docker.sock exists and is a socket
  └── assert phpbb_traefik_docker_network exists

install.yml
  ├── create phpbb_compose_dir (mode 0750)
  ├── render templates/compose.yml.j2 → compose.yml (mode 0640)
  │     notifies: restart phpbb, restart mysql
  └── render templates/env.secrets.j2 → .env.secrets (mode 0600, no_log)
        notifies: restart phpbb, restart mysql

service.yml
  └── docker_compose_v2: project_src=phpbb_compose_dir, state=present

verify.yml
  ├── poll phpbb container until State.Health.Status == healthy
  └── poll phpbb-mysql container until State.Health.Status == healthy
```

---

## Consumer side

This role is consumed from a playbooks repo. The consuming host must have:

* Docker Engine installed and running.
* [`ansible-role-traefik`](https://github.com/basictheprogram/ansible-role-traefik) applied first (creates the `traefik_proxy` network
  and starts Traefik).
* `host_vars/<host>/vault.yml` with the three secret variables, encrypted
  with `ansible-vault`.

### Minimal host_vars example

`host_vars/forum.example.com/phpbb.yml`:

```yaml
phpbb_domain: forum.example.com
phpbb_tz: America/Chicago
phpbb_apache_server_admin: admin@example.com
phpbb_mysql_database: phpbb3
phpbb_mysql_user: phpbb
```

`host_vars/forum.example.com/vault.yml` (encrypted):

```yaml
phpbb_mysql_root_password: "{{ vault_phpbb_mysql_root_password }}"
phpbb_mysql_password: "{{ vault_phpbb_mysql_password }}"
phpbb_database_password: "{{ vault_phpbb_database_password }}"
```

`playbook.yml`:

```yaml
- hosts: forum
  roles:
    - role: realtime.traefik
    - role: realtime.docker_phpbb
```

---

## Open questions

* **`remoteip.conf` Traefik IP.** The phpBB image hard-codes `172.18.0.2` as
  the trusted Traefik proxy IP inside Apache. This will silently pass the wrong
  client IP to phpBB if the Docker network assigns a different address.
  Resolution options: parameterise in the image build via a build arg, or
  override at container runtime via an env var and entrypoint logic. Tracked
  in TODO.md.

* **phpBB image tag pinning.** The role defaults to `latest`. For production
  deployments the image should be pinned to a digest or semver tag. This
  requires the dedicated image repo to publish versioned releases.

* **Backup and restore.** No tasks or runbook exist for migrating the live
  named volumes from the original Docker Compose host to a new
  Ansible-managed deployment. Tracked in TODO.md.
