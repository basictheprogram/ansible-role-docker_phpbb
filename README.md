# Ansible Role: docker_phpbb

[![CI](https://github.com/basictheprogram/ansible-role-docker_phpbb/actions/workflows/ci.yml/badge.svg)](https://github.com/basictheprogram/ansible-role-docker_phpbb/actions/workflows/ci.yml)
[![Ansible Galaxy](https://img.shields.io/badge/ansible--galaxy-realtime.docker__phpbb-blue.svg?style=popout-square)](https://galaxy.ansible.com/ui/standalone/roles/realtime/docker_phpbb/)
[![Ansible Role](https://img.shields.io/ansible/role/d/realtime/docker_phpbb.svg?style=popout-square)](https://galaxy.ansible.com/ui/standalone/roles/realtime/docker_phpbb/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg?style=popout-square)](LICENSE)
[![ansible-core](https://img.shields.io/badge/ansible--core-%3E%3D2.20-lightgrey.svg?style=popout-square)](https://docs.ansible.com/ansible/latest/installation_guide/intro_installation.html)

Deploys [phpBB3](https://www.phpbb.com/) and MySQL as Docker Compose services
on a single Docker host. Assumes [Traefik](https://traefik.io/) is already
running and managing TLS, deployed via [`ansible-role-traefik`](https://github.com/basictheprogram/ansible-role-traefik).

> For full architecture, schemas, and design decisions see [DESIGN.md](DESIGN.md).

## Requirements

- Ansible core >= 2.20
- `community.docker` collection
- Docker Engine installed and running on the target host
- [`ansible-role-traefik`](https://github.com/basictheprogram/ansible-role-traefik) applied before this role (creates the Docker network
  and starts Traefik)

## Supported Platforms

| OS     | Versions                          |
|--------|-----------------------------------|
| Ubuntu | jammy (22.04), noble (24.04), resolute (26.04) |
| Debian | bookworm (12), trixie (13)        |

## Role Variables

### defaults/main.yml

| Variable | Default | Description |
|---|---|---|
| `phpbb_image` | `basictheprogram/crossfire-phpbb3:latest` | phpBB container image |
| `phpbb_container_name` | `phpbb` | phpBB container name |
| `phpbb_restart_policy` | `unless-stopped` | phpBB restart policy |
| `phpbb_mysql_image` | `mysql:lts` | MySQL container image |
| `phpbb_mysql_container_name` | `phpbb-mysql` | MySQL container name |
| `phpbb_mysql_restart_policy` | `unless-stopped` | MySQL restart policy |
| `phpbb_compose_dir` | `/opt/phpbb` | Host directory for compose files |
| `phpbb_traefik_docker_network` | `traefik_proxy` | External Docker network name; must match `traefik_docker_network` in [`ansible-role-traefik`](https://github.com/basictheprogram/ansible-role-traefik) |
| `phpbb_tz` | `UTC` | Timezone for both containers |
| `phpbb_compose_log_driver` | `journald` | Docker logging driver |
| `phpbb_journald_tag_phpbb` | `phpbb.{{ inventory_hostname }}` | journald tag for phpBB container |
| `phpbb_journald_tag_mysql` | `phpbb-mysql.{{ inventory_hostname }}` | journald tag for MySQL container |
| `phpbb_domain` | `""` | **Required.** FQDN for phpBB (e.g. `forum.example.com`) |
| `phpbb_traefik_entrypoint` | `websecure` | Traefik entrypoint name |
| `phpbb_traefik_certresolver` | `letsencrypt` | Traefik cert resolver name |
| `phpbb_mysql_database` | `phpbb3` | MySQL database name |
| `phpbb_mysql_user` | `phpbb` | MySQL user for phpBB |
| `phpbb_mysql_host_port` | `3306` | MySQL port |
| `phpbb_database_host` | `{{ phpbb_mysql_container_name }}` | Database hostname seen by phpBB |
| `phpbb_apache_server_admin` | `webmaster@localhost` | Apache ServerAdmin email |
| `phpbb_verify_healthcheck` | `true` | Poll containers until healthy after deploy |
| `phpbb_verify_healthcheck_retries` | `10` | Number of health poll retries |
| `phpbb_verify_healthcheck_delay` | `15` | Seconds between health poll retries |

### Secrets (vault in host_vars)

These must be set and encrypted with `ansible-vault` in
`host_vars/<host>/vault.yml`. Never set them in `defaults/main.yml`.

| Variable | Description |
|---|---|
| `phpbb_mysql_root_password` | MySQL root password |
| `phpbb_mysql_password` | MySQL password for the phpBB user |
| `phpbb_database_password` | phpBB application database password (must match `phpbb_mysql_password`) |

## Task Flow

1. **Preflight** — asserts Ansible version, required variables, Docker socket
   availability, and that the Traefik Docker network already exists.
2. **Install** — creates `phpbb_compose_dir`, renders `compose.yml` from
   template, renders `.env.secrets` (mode 0600).
3. **Service** — runs `community.docker.docker_compose_v2` to bring up the
   MySQL and phpBB containers.
4. **Verify** — polls `docker inspect` until both containers report a healthy
   healthcheck status.

## Example Playbook

```yaml
- hosts: forum
  roles:
    - role: realtime.traefik
    - role: realtime.docker_phpbb
```

### host_vars/forum.example.com/phpbb.yml

```yaml
phpbb_domain: forum.example.com
phpbb_tz: America/Chicago
phpbb_apache_server_admin: admin@example.com
phpbb_traefik_certresolver: letsencrypt
```

### host_vars/forum.example.com/vault.yml (encrypted)

```yaml
phpbb_mysql_root_password: "{{ vault_phpbb_mysql_root_password }}"
phpbb_mysql_password: "{{ vault_phpbb_mysql_password }}"
phpbb_database_password: "{{ vault_phpbb_database_password }}"
```

## Docker Volumes

The role creates and manages the following named Docker volumes:

| Volume | Mounted at | Contents |
|---|---|---|
| `phpbb-mysql-data` | `/var/lib/mysql` | MySQL data directory |
| `phpbb_config` | `/config-volume` | `config.php` (DB credentials) |
| `phpbb_files` | `…/phpBB3/files` | User uploads |
| `phpbb_images` | `…/phpBB3/images` | Custom images and avatars |
| `phpbb_store` | `…/phpBB3/store` | Cache and backups |
| `phpbb_ext` | `…/phpBB3/ext` | phpBB extensions |

## License

MIT

## Author

Bob Tanner
