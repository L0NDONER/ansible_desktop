#!/usr/bin/env python3
import os
import re

# Sensitive patterns to look for
SENSITIVE_KEYWORDS = ['password', 'token', 'secret', 'api_key', 'sid', 'auth', 'become_pass']

def scan_dry_run():
    base_path = os.path.expanduser("~/ansible")
    print(f"🕵️  SCANNING: Checking {base_path} for unencrypted secrets...")
    
    found_count = 0
    for root, dirs, files in os.walk(base_path):
        if '.git' in root or '__pycache__' in root: continue
        
        for file in files:
            file_path = os.path.join(root, file)
            try:
                with open(file_path, 'r', errors='ignore') as f:
                    lines = f.readlines()
                    
                    # 1. Skip files already encrypted with Ansible Vault
                    content = ''.join(lines)
                    if "$ANSIBLE_VAULT;" in content: continue
                    
                    for line_num, line in enumerate(lines, 1):
                        # Skip comments
                        stripped = line.strip()
                        if stripped.startswith('#'):
                            continue
                        
                        # Skip YAML list items that are quoted strings (display messages)
                        if re.match(r'^\s*-\s*["\']', stripped):
                            continue
                        
                        for key in SENSITIVE_KEYWORDS:
                            # Match patterns like:
                            #   password: value
                            #   my_password: value  
                            #   password_file: value
                            # But NOT:
                            #   wireguard_password_hash: {{ vault_var }}
                            #   some_other_password_thing: {{ vault_var }}
                            
                            # Look for the keyword with optional prefix/suffix but check if value is templated
                            pattern = fr'\w*{key}\w*\s*[:=]\s*(.+)'
                            
                            matches = re.finditer(pattern, line, re.IGNORECASE)
                            for match in matches:
                                full_match = match.group(0)
                                value = match.group(1).strip()
                                
                                # Skip if the value contains Jinja2 template syntax
                                if '{{' in value or '}}' in value:
                                    continue
                                
                                # Skip if this looks like a hash/encoded version (ends with _hash, _encrypted, etc)
                                if re.search(r'_(hash|encrypted|vault|encoded)\s*[:=]', full_match, re.IGNORECASE):
                                    continue
                                
                                # Skip if this is a file path reference (ends with _file)
                                if re.search(r'_file\s*[:=]', full_match, re.IGNORECASE):
                                    continue
                                    
                                print(f"🚩 FLAG: {file_path}:{line_num}")
                                print(f"   Keyword: {key}")
                                print(f"   Line: {line.strip()}")
                                print()
                                found_count += 1
                                break
            except: continue
    
    print(f"✅ Scan complete. Found {found_count} items requiring review.")

if __name__ == "__main__":
    scan_dry_run()
