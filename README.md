# 🚀 Production-Grade Infrastructure Automation

> **Self-healing, GitOps-managed, multi-cloud infrastructure with WhatsApp command center**

[![Ansible](https://img.shields.io/badge/Ansible-2.9+-red.svg)](https://www.ansible.com/)
[![Python](https://img.shields.io/badge/Python-3.x-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-Personal-green.svg)](LICENSE)

**What started as basic Ansible automation evolved into a production-grade, self-healing infrastructure spanning AWS, home lab, and desktop environments - all manageable via WhatsApp from a delivery van.**

---

## 🎯 What This Actually Is

This isn't just "configuration management." This is:

- ✅ **Self-Healing Infrastructure** - VPN automatically recovers from failures
- ✅ **GitOps Automation** - Nightly pulls from GitHub, zero manual intervention
- ✅ **WhatsApp Command Center** - Control your entire stack via text message
- ✅ **Multi-Cloud Orchestration** - AWS, home Raspberry Pi, Linux desktop
- ✅ **Production Uptime** - 1200+ days on critical services
- ✅ **Zero-Trust Security** - Vault encryption, secret scanning, SSH hardening
- ✅ **Event-Driven Architecture** - Automated responses to infrastructure events

---

## 🏗️ Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                     GitOps Repository                        │
│  (This Repo - Single Source of Truth)                       │
└──────────────────┬──────────────────────────────────────────┘
                   │
                   ↓ (ansible-pull @ 1am nightly)
        ┌──────────┴──────────┬─────────────┐
        ↓                     ↓             ↓
┌───────────────┐    ┌────────────────┐   ┌──────────────┐
│ Linux Mint    │    │ Raspberry Pi   │   │   AWS EC2    │
│ (Desktop)     │    │ (Pi-hole DNS)  │   │ (WireGuard)  │
│               │    │                │   │              │
│ • Python Dev  │    │ • DNS Filter   │   │ • VPN Server │
│ • Media Auto  │    │ • 1200d Uptime │   │ • Self-Heal  │
│ • Commander   │    │ • Network Svcs │   │ • Monitoring │
└───────────────┘    └────────────────┘   └──────────────┘
        │                     │                    │
        └─────────────────────┴────────────────────┘
                              │
                    ┌─────────┴─────────┐
                    ↓                   ↓
            ┌───────────────┐   ┌──────────────┐
            │ Commander Bot │   │  Watchdog    │
            │ (WhatsApp)    │   │  (Auto-Heal) │
            └───────────────┘   └──────────────┘
```

---

## 🔥 Key Features

### 🤖 WhatsApp Commander Bot

Control your entire infrastructure via WhatsApp messages:

```
You: "addtv The Last of Us"
Bot: ✅ Added TV show: The Last of Us
     [Auto-downloads episodes via autodl-irssi]

You: "healvpn"
Bot: 🔧 VPN healing initiated!
     [Runs ansible-playbook aws.yml --tags wireguard]

You: "stats"
Bot: 💻 Minty System Stats
     ⏰ up 47 days, 3 hours
     💾 Disk: 67% used
     🧠 RAM: 3.2G/7.7G
```

**Commands:** `update`, `healvpn`, `addtv`, `addmovie`, `seeding`, `stats`

### 🏥 Self-Healing VPN Infrastructure

WireGuard VPN automatically recovers from failures:

1. **Watchdog monitors** VPN health every hour
2. **Detects failures** (502/504/timeout)
3. **Auto-heals** by redeploying WireGuard container
4. **Notifies via WhatsApp** when recovery completes
5. **Anti-flap protection** prevents recovery loops

**Result:** Zero-touch VPN reliability with SMS alerts.

### 🔄 GitOps Workflow

Infrastructure updates automatically from GitHub:

```bash
# You (4pm): Code changes, git push
# System (1am): ansible-pull runs automatically
# Result (1:05am): All hosts updated, WhatsApp confirmation
```

**Benefits:**
- Version-controlled infrastructure
- Automatic deployment across fleet
- Rollback via git revert
- Audit trail of all changes

### 🛡️ Security Hardening

Multiple layers of security protection:

- **Ansible Vault** - AES-256 encrypted credentials
- **Pre-commit Hooks** - Blocks commits containing plain-text secrets
- **SSH Hardening** - Key-only auth, root login disabled, custom banner
- **UFW Firewall** - Automated configuration across all hosts
- **Secret Scanner** - Custom Python tool prevents credential leaks

### 📦 Fleet Management

88 automated tasks across 3 hosts:

```
PLAY RECAP *************************************************
aws-vpn    : ok=33  changed=2  failed=0  ✅
localhost  : ok=31  changed=2  failed=0  ✅
pihole     : ok=23  changed=0  failed=0  ✅
```

**Managed automatically:**
- System updates & security patches
- SSH hardening & banners
- Python environments
- Flatpak applications
- Docker containers
- WireGuard VPN
- Automated backups

---

## 📂 Repository Structure

```
ansible/
├── Core Orchestration
│   ├── local.yml                    # Main entry point
│   ├── mastersite.yml               # Fleet orchestrator
│   ├── maintenance.yml              # System updates module
│   └── gitops-setup.yml             # Bootstrap new hosts
│
├── Infrastructure Components
│   ├── aws.yml                      # AWS EC2 configuration
│   ├── pi.yml                       # Raspberry Pi setup
│   ├── wireguard.yml                # VPN deployment
│   ├── wireguard-management.yml     # VPN backup/restore
│   └── watchdog.yml                 # Self-healing logic
│
├── Task Modules (Modular Design)
│   ├── ssh_harden.yml               # SSH security
│   ├── update.yml                   # APT updates
│   ├── python.yml                   # Python env setup
│   ├── flatpaks.yml                 # Flatpak management
│   ├── aptcleanup.yml               # Disk cleanup
│   └── third-party-software.yml     # Additional packages
│
├── Automation Services
│   ├── commander.py                 # WhatsApp bot (Flask)
│   ├── dashboard.py                 # Streamlit metrics
│   └── secret_scan.py               # Pre-commit security
│
├── Configuration
│   ├── ansible.cfg                  # Ansible settings
│   ├── inventory.ini                # Host definitions (gitignored)
│   └── group_vars/all.yml           # Vault-encrypted secrets
│
└── Documentation
    ├── README.md                    # This file
    └── install-git-hook.sh          # Security setup
```

---

## 🚀 Quick Start

### Prerequisites

```bash
# On control machine (your desktop)
sudo apt install ansible python3-pip
pip3 install twilio flask streamlit

# Generate Ansible Vault password
openssl rand -base64 32 > ~/.vault_pass
chmod 600 ~/.vault_pass
```

### Installation

```bash
# 1. Clone repository
git clone https://github.com/L0NDONER/ansible_desktop.git
cd ansible_desktop

# 2. Create inventory
cat > inventory.ini << EOF
[ubuntu]
localhost ansible_connection=local ansible_user=martin

[pi]
pihole ansible_host=192.168.1.100 ansible_user=pi

[aws]
aws-vpn ansible_host=YOUR_AWS_IP ansible_user=ubuntu
EOF

# 3. Encrypt secrets
ansible-vault create group_vars/all.yml
# Add your variables (see Configuration section)

# 4. Install git hook (prevents secret leaks)
bash install-git-hook.sh

# 5. Bootstrap GitOps on all hosts
ansible-playbook gitops-setup.yml -i inventory.ini --ask-vault-pass
```

### Configuration

Create `group_vars/all.yml` with your secrets:

```yaml
---
# Twilio (for WhatsApp Commander)
twilio_sid: "AC1234567890abcdef"
tw_auth_k: "your_auth_token"
twilio_from_number: "+14155238886"
my_mobile_number: "+447123456789"

# Ansible
ansible_vault_password: "your_vault_password"

# WireGuard
vault_wireguard_password_hash: "$2b$12$..."
```

Then encrypt it:
```bash
ansible-vault encrypt group_vars/all.yml
```

---

## 📖 Usage Examples

### Fleet Management

```bash
# Update all hosts
ansible-playbook mastersite.yml -i inventory.ini --ask-vault-pass

# Update specific host
ansible-playbook mastersite.yml -i inventory.ini --limit aws-vpn --ask-vault-pass

# Dry run (check mode)
ansible-playbook mastersite.yml -i inventory.ini --check --ask-vault-pass

# View playbook output with timing
ansible-playbook mastersite.yml -i inventory.ini --ask-vault-pass -v
```

### WireGuard Management

```bash
# Deploy/update WireGuard
ansible-playbook wireguard.yml -i inventory.ini --ask-vault-pass

# Backup configs
ansible-playbook wireguard-management.yml -i inventory.ini --ask-vault-pass

# Just firewall rules
ansible-playbook wireguard.yml --tags firewall --ask-vault-pass

# Health check only
ansible-playbook wireguard.yml --tags health --ask-vault-pass
```

### WhatsApp Commander

```bash
# Start the bot (or use systemd service)
python3 commander.py

# Or enable as service (handled by gitops-setup.yml)
sudo systemctl status commander.service
```

Then text commands to your WhatsApp bot number:
- `update` - Trigger ansible-pull
- `healvpn` - Restart VPN
- `addtv Breaking Bad` - Add TV show filter
- `stats` - System resource usage

### Watchdog Monitoring

```bash
# Run watchdog manually
ansible-playbook watchdog.yml -i inventory.ini --ask-vault-pass

# Check systemd timer status
sudo systemctl status ansible-pull.timer
journalctl -u ansible-pull.service
```

---

## 🔧 Advanced Features

### Tagged Execution

Playbooks use tags for surgical updates:

```bash
# Just SSH hardening
ansible-playbook mastersite.yml --tags ssh -i inventory.ini --ask-vault-pass

# Just Python setup
ansible-playbook mastersite.yml --tags python -i inventory.ini --ask-vault-pass

# Multiple tags
ansible-playbook mastersite.yml --tags "docker,wireguard" -i inventory.ini --ask-vault-pass
```

### Modular Task Design

Each task module is independent and reusable:

```yaml
# In maintenance.yml
- name: Apply SSH Hardening and Banners
  include_tasks: ssh_harden.yml

- name: Install Third Party Software
  include_tasks: third-party-software.yml
```

Benefits:
- Easy to debug (small files)
- Reusable across playbooks
- Clear separation of concerns
- Version control friendly

### Block/Rescue Pattern

Intelligent error handling with targeted notifications:

```yaml
- name: Main Fleet Update Block
  block:
    - name: Run System Updates
      include_tasks: update.yml
    # ... more tasks ...
  rescue:
    - name: Send Failure WhatsApp
      community.general.twilio:
        msg: |
          🚨 Ansible Fleet ALERT
          Failed Task: {{ ansible_failed_task.name }}
          Error: {{ ansible_failed_result.msg }}
```

### Anti-Flap Protection

Prevents recovery loops in watchdog:

```yaml
- name: Check last healing timestamp
  stat:
    path: /tmp/vpn_last_heal
  register: last_heal

- name: Determine if healing needed
  set_fact:
    cooldown_active: >-
      {{ (current_time - last_heal_time) < 600 }}  # 10 min cooldown
```

---

## 🎯 Real-World Use Cases

### Scenario 1: Adding a TV Show While Driving

```
7:23am - In delivery van, podcast mentions "Fallout" series
         Pull over safely, grab phone

You (WhatsApp): "addtv Fallout"
Bot: ✅ Added TV show: Fallout

[Behind the scenes:]
→ commander.py receives webhook from Twilio
→ Adds filter to ~/.autodl/autodl.cfg
→ Reloads autodl-irssi via screen command
→ IRC bot starts monitoring for "Fallout" releases

9:00am - Episode releases
         autodl-irssi auto-downloads
         JellyLink processes and moves to library

3:00pm - Arrive home, episode ready to watch
```

### Scenario 2: VPN Failure at Night

```
1:00am - You're asleep
         watchdog.yml runs via systemd timer
         Detects VPN returning 502 Gateway Error

[Auto-healing sequence:]
1:01am - Triggers: ansible-playbook aws.yml --tags wireguard
1:02am - Stops wg-easy container
1:03am - Redeploys container from latest image
1:04am - Waits for port 51821 to respond
1:05am - Verifies WireGuard interface is up
1:06am - WhatsApp: "🔐 WireGuard VPN Deployed - 2 peers connected"

7:00am - You wake up, check phone
         See auto-heal notification
         VPN has been working all night
         Continue delivering parcels
```

### Scenario 3: New Host Bootstrap

```bash
# Got a new Raspberry Pi for monitoring
# Add to inventory.ini
echo "new-pi ansible_host=192.168.1.50 ansible_user=pi" >> inventory.ini

# Run GitOps bootstrap
ansible-playbook gitops-setup.yml -i inventory.ini --limit new-pi --ask-vault-pass

# 2 minutes later:
# ✅ Ansible-pull timer configured (runs nightly at 1am)
# ✅ Commander bot running
# ✅ Dashboard accessible on port 8501
# ✅ SSH hardened, vault password deployed
# ✅ Auto-updates enabled

# From now on, this Pi updates itself automatically
```

---

## 🛡️ Security

### Secret Management

**Three layers of protection:**

1. **Ansible Vault** - Encrypt credentials at rest
2. **Jinja2 Templates** - Separate secrets from code
3. **Pre-commit Hook** - Block commits with plain-text secrets

```bash
# Create encrypted secrets
ansible-vault create group_vars/all.yml

# Edit encrypted secrets
ansible-vault edit group_vars/all.yml

# View without editing
ansible-vault view group_vars/all.yml

# Decrypt (emergency only)
ansible-vault decrypt group_vars/all.yml
```

### Secret Scanner

Custom Python tool prevents credential leaks:

```bash
# Scans before every git commit
git commit -m "Updated config"

🕵️  SCANNING: Checking ~/ansible for unencrypted secrets...
✅ SCAN PASSED: No unencrypted secrets detected
```

**Smart Detection:**
- ✅ Ignores Jinja2 templates: `{{ vault_password }}`
- ✅ Ignores hash variables: `password_hash: $2b$...`
- ✅ Ignores file paths: `vault_password_file: ~/.vault_pass`
- ✅ Ignores comments: `# password: example`
- 🚨 Blocks plain text: `password: MyS3cr3tP@ss`

### SSH Hardening

Automatic security configuration:

```yaml
# Applied to all hosts
- PasswordAuthentication no
- PermitRootLogin no
- AllowUsers martin ubuntu
- Banner /etc/ssh/banner.txt
```

Custom banner:
```
#################################################################################
#                                                                               #
#             IF YOU ARE NOT MARTIN OR UBUNTU, KINDLY FUCK OFF.                 #
#                                                                               #
#################################################################################
```

---

## 📊 Monitoring & Observability

### Dashboard (Streamlit)

Web-based metrics on port 8501:
- Torrent seeding ratios
- Media library statistics
- System resource usage
- Disk space monitoring

Access: `http://localhost:8501`

### WhatsApp Notifications

Real-time alerts for:
- ✅ Fleet update completion
- 🚨 Task failures with error details
- 🔐 VPN auto-healing events
- ⚠️ SSL certificate expiry warnings
- 📊 System stats on demand

### Logging

All automation logged via systemd journal:

```bash
# View ansible-pull logs
journalctl -u ansible-pull.service -f

# View commander bot logs
journalctl -u commander.service -f

# View watchdog logs
journalctl -u watchdog.timer -f
```

---

## 🔬 Technical Deep Dive

### GitOps Implementation

**Nightly Pull Architecture:**

```yaml
# systemd timer: ansible-pull.timer
[Timer]
OnCalendar=*-*-* 01:00:00
RandomizedDelaySec=300      # Prevents thundering herd
Persistent=true

# systemd service: ansible-pull.service
ExecStart=/usr/bin/ansible-pull \
  -U https://github.com/L0NDONER/ansible_desktop.git \
  -C main \
  --vault-password-file ~/.ansible/vault_pass.txt \
  local.yml
```

**Workflow:**
1. Timer triggers at 1am (±5 min)
2. Git pull from GitHub (main branch)
3. Decrypt vault secrets
4. Run local.yml playbook
5. Log results to journal
6. WhatsApp notification on completion

### Self-Healing Logic

**Watchdog Decision Tree:**

```python
if vpn_health_check.failed or vpn_health_check.status in [502, 504]:
    if not cooldown_active:
        # Run healing playbook
        subprocess.run([
            "ansible-playbook",
            "aws.yml",
            "--tags", "wireguard"
        ])
        # Mark healing timestamp
        # Send WhatsApp notification
    else:
        # Skip healing (anti-flap)
        # Wait for cooldown to expire
```

### WhatsApp Integration

**Twilio Webhook Flow:**

```
User Phone → WhatsApp Message
    ↓
Twilio (receives message)
    ↓
POST https://your-server.com/webhook
    ↓
Flask App (commander.py)
    ↓
Parse command & execute
    ↓
Return TwiML Response
    ↓
Twilio → WhatsApp Reply to User
```

**Security:**
- Only authorized number can send commands
- Input sanitization on all user input
- No shell injection (uses subprocess.run with list args)
- Rate limiting possible (not currently implemented)

---

## 🎓 Lessons Learned

### What Worked Well

✅ **Modular task files** - Easy to debug and maintain  
✅ **Block/rescue pattern** - Intelligent error handling  
✅ **Tagged execution** - Surgical updates without full runs  
✅ **GitOps workflow** - Version control everything  
✅ **Secret scanning** - Prevented credential leaks  
✅ **WhatsApp integration** - Remote control from anywhere  

### What I'd Do Differently

🔄 **Earlier secret scanning** - Implement from day 1  
🔄 **More comprehensive logging** - Structured logs from the start  
🔄 **Testing framework** - Ansible Molecule for task validation  
🔄 **Backup verification** - Automated restore testing  

### Performance Optimizations

Applied over time:
- SSH pipelining (3x speed improvement)
- ControlMaster (reused connections)
- Parallel execution (forks=5)
- Smart change detection (reduced unnecessary work)

---

## 📈 Project Evolution

### v0.01 (2022)
- Basic system updates
- Manual execution
- Plain-text credentials 😱

### v0.10 (2023)
- Added WireGuard automation
- Vault encryption
- Modular task design

### v0.15 (2024)
- GitOps workflow
- WhatsApp Commander
- Self-healing watchdog

### v0.20 (2025)
- Secret scanner
- Multi-cloud orchestration
- Production-grade reliability

### Future Roadmap
- [ ] Prometheus metrics export
- [ ] Grafana dashboards
- [ ] Automated disaster recovery testing
- [ ] Multi-region failover
- [ ] Kubernetes migration (maybe)

---

## 🤝 Contributing

This is personal infrastructure, but if you're forking:

1. **Update inventory** with your own hosts
2. **Re-encrypt secrets** with your vault password
3. **Modify variables** (IPs, usernames, etc.)
4. **Test in check mode** before applying
5. **Install git hooks** for security

**Pull requests welcome** for:
- Bug fixes
- Performance improvements
- Additional task modules
- Documentation improvements

---

## 📜 License

Personal use only. Feel free to learn from it, but don't copy for commercial use.

---

## 👨‍💻 Author

**Martin O'Flaherty**

Courier driver by morning (4am-2pm), infrastructure engineer by evening (4pm-11pm).

*Built with Python, Ansible, and determination while everyone else was asleep.*

---

## 🙏 Acknowledgments

- **Raspberry Pi Community** - For being welcoming when Arch Linux forums weren't
- **Ansible Documentation** - Comprehensive and actually useful
- **Stack Overflow** - For the 2am debugging sessions
- **Twilio** - For making WhatsApp bots possible
- **Coffee** - Obviously

---

## 📞 Support

This is personal infrastructure, so no formal support. But if you find bugs:

1. Check existing issues
2. Create detailed bug report with:
   - Ansible version
   - OS/distribution
   - Error output
   - Steps to reproduce

---

**Last Updated:** January 2026  
**Version:** 0.20  
**Status:** Production (1200+ days uptime on critical services)

---

*"Just start with two sentences and iterate." - The philosophy that built this.*
