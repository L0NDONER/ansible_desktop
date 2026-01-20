# Ansible Infrastructure Automation

Multi-host infrastructure automation for managing Linux desktop, Raspberry Pi, and AWS EC2 environments.

## Overview

This repository contains Ansible playbooks for automated management of:
- **Linux Mint Desktop** - System updates, flatpak management, third-party software
- **Raspberry Pi (Pi-hole)** - DNS filtering and network services
- **AWS EC2 (VPN Server)** - WireGuard VPN with wg-easy management interface

## Features

- 🔐 **Vault-encrypted credentials** for secure password management
- 🔄 **Automated system updates** across all hosts
- 🐳 **Docker container management** (Nginx, WireGuard)
- 📦 **Flatpak application updates** with smart change detection
- 💾 **Automated WireGuard backups** - Database and configuration files
- 🔧 **Modular task structure** for maintainability
- 🎯 **Tagged playbooks** for selective execution

## Prerequisites

- Ansible 2.9+ installed on control machine
- SSH access to all managed hosts
- Ansible Vault password for encrypted credentials
- Python 3.x on all managed hosts

## Repository Structure

```
.
├── ansible.cfg                    # Ansible configuration
├── local.yml                      # Main orchestration playbook
├── ansible_passwords.yml          # Vault-encrypted credentials
├── inventory                      # Host definitions (not in repo)
├── aws.yml                        # AWS EC2 configuration
├── pi.yml                         # Raspberry Pi configuration
├── wireguard-management.yml       # WireGuard automation
├── flatpaks.yml                   # Flatpak update tasks
├── update.yml                     # System update tasks
├── aptcleanup.yml                 # APT cache cleanup
├── python.yml                     # Python environment setup
├── sshfs.yml                      # SSHFS mount configuration
└── third-party-software.yml       # Additional software installation
```

## Quick Start

### 1. Clone the Repository

```bash
git clone <your-repo-url>
cd ansible_desktop
```

### 2. Configure Inventory

Create an `inventory` file (gitignored) with your hosts:

```ini
[ubuntu]
localhost ansible_connection=local

[pi]
pihole ansible_host=<pi-ip-address>

[aws]
aws-vpn ansible_host=<aws-public-ip>
```

### 3. Run Playbooks

**Update all hosts:**
```bash
ansible-playbook local.yml --ask-vault-pass
```

**Target specific hosts:**
```bash
# Update only Raspberry Pi
ansible-playbook local.yml --tags pi --ask-vault-pass

# Update only AWS infrastructure
ansible-playbook local.yml --tags aws --ask-vault-pass

# Manage WireGuard only
ansible-playbook local.yml --tags wireguard --ask-vault-pass
```

**Dry run (check mode):**
```bash
ansible-playbook local.yml --ask-vault-pass --check
```

## WireGuard Management

The `wireguard-management.yml` playbook provides automated management of WireGuard VPN:

### Features
- Automatic database backups with timestamps
- Client configuration extraction from SQLite
- Server configuration backup
- Generates comprehensive management guide
- Optional client deployment to localhost

### Usage

```bash
# Run WireGuard management tasks
ansible-playbook local.yml --tags wireguard --ask-vault-pass
```

### Output

Backups and guides are saved to `~/wireguard-clients/`:
- `wg-easy-backup-YYYY-MM-DD.db` - SQLite database backup
- `wg0-server-config.conf` - WireGuard server configuration
- `WIREGUARD-GUIDE.txt` - Management instructions and client list

### Web Interface

Access wg-easy web UI at: `http://<your-aws-ip>:51821`

## Configuration Management

### Ansible Vault

Sensitive credentials are encrypted using Ansible Vault:

**View encrypted files:**
```bash
ansible-vault view ansible_passwords.yml
```

**Edit encrypted files:**
```bash
ansible-vault edit ansible_passwords.yml
```

**Create new encrypted files:**
```bash
ansible-vault create new_secrets.yml
```

### SSH Configuration

The playbook uses a dedicated SSH key (`~/.ssh/ansible`). Ensure this key is:
- Generated and added to all managed hosts
- Has appropriate permissions (0600)
- Added to `~/.ssh/config` if needed

## Performance Optimizations

The configuration includes several optimizations:

- **SSH Pipelining** - Reduces SSH operations for faster execution
- **ControlMaster** - Reuses SSH connections
- **Profile Tasks** - Identifies slow tasks for optimization
- **Parallel Execution** - Manages multiple hosts concurrently

## Playbook Details

### local.yml (Main Orchestration)

Executes tasks on Ubuntu hosts and imports specialized playbooks:
- System updates and package management
- Third-party software installation
- Python environment setup
- Flatpak updates
- Automatic reboot handling

### wireguard-management.yml

Comprehensive WireGuard VPN management:
- Container health checks
- Database backups and extraction
- Client list retrieval
- Optional client deployment

### aws.yml

AWS EC2 configuration:
- Nginx container on port 8080 (wg-easy interface)
- WireGuard on port 80 (for firewall traversal)

### flatpaks.yml

Intelligent Flatpak management:
- Non-interactive updates
- Graceful failure handling
- Smart change detection

## Troubleshooting

### Connection Issues

```bash
# Test connectivity to hosts
ansible all -m ping

# Verbose output for debugging
ansible-playbook local.yml --ask-vault-pass -vvv
```

### Vault Password Issues

If you forget your vault password, you'll need to:
1. Recreate encrypted files
2. Re-encrypt with new password

### SSH Key Problems

Ensure your SSH key is properly configured:
```bash
# Test SSH access
ssh -i ~/.ssh/ansible user@host

# Verify key permissions
chmod 600 ~/.ssh/ansible
```

## Security Considerations

- ✅ Never commit `inventory` file with real IPs/hostnames
- ✅ Never commit `.vault_pass` or vault passwords
- ✅ Never commit SSH private keys
- ✅ Keep `ansible_passwords.yml` encrypted at all times
- ✅ Restrict WireGuard web interface access via security groups
- ✅ Use strong vault passwords

## Best Practices

1. **Test in check mode first** - Always use `--check` before applying changes
2. **Tag your playbooks** - Enable selective execution
3. **Keep backups** - WireGuard configs are automatically backed up
4. **Monitor changes** - Review task output for unexpected modifications
5. **Version control** - Commit changes with clear messages

## Contributing

This is a personal infrastructure repository. If you're forking this:

1. Update the `inventory` file with your hosts
2. Re-encrypt `ansible_passwords.yml` with your vault password
3. Modify variables in playbooks to match your infrastructure
4. Update AWS IP references in `wireguard-management.yml`

## License

Personal use only.

## Author

Martin O'Flaherty

---

**Version:** 0.03  
**Last Updated:** January 2026
