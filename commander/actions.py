import subprocess
import psutil
import os
import json
import requests
from . import config

def handle_disk_command():
    try:
        usage = psutil.disk_usage('/')
        percent = usage.percent
        status = "🚨" if percent > 90 else "⚠️" if percent > 75 else "✅"
        return (
            f"💽 *Disk Usage (Root)*\n"
            f"Used: {usage.used // (2**30)}GB / {usage.total // (2**30)}GB ({percent}%)\n"
            f"Status: {status}"
        )
    except Exception as e:
        return f"❌ Disk check error: {str(e)}"

def handle_fleet_command():
    hosts = []
    if os.path.exists(config.INVENTORY_PATH):
        with open(config.INVENTORY_PATH, 'r') as f:
            for line in f:
                if line.strip() and not line.strip().startswith(('[', '#', ';')):
                    h = line.split()[0]
                    if '=' not in h and h.upper() != 'MINTY': hosts.append(h)
    
    response = "🌐 *Minty Fleet Dashboard*"
    for host in (['localhost'] + hosts):
        try:
            if host == 'localhost':
                with open('/tmp/fleet_health.json', 'r') as f: data = json.load(f)
            else:
                raw = subprocess.check_output(["ssh", "-o", "ConnectTimeout=2", host, "cat /tmp/fleet_health.json"], timeout=3).decode()
                data = json.loads(raw)
            response += f"\n\n*{host.upper()}*\n┣ ⏱️ {data.get('uptime','n/a')}\n┣ 🛡️ {data.get('knocks','0')} hits"
        except:
            response += f"\n\n🔴 *{host.upper()}* (down)"
    return response

def handle_pingall_command():
    try:
        out = subprocess.check_output([
            "ansible", "all", "-m", "ping", "-i", config.INVENTORY_PATH, "--vault-password-file", config.VAULT_PASS_FILE
        ], timeout=15).decode()
        pong_count = out.count('"ping": "pong"')
        total_count = out.count('SUCCESS') + out.count('UNREACHABLE')
        return f"🟢 Fleet ping\n✅ Online: {pong_count}/{total_count}"
    except Exception as e: 
        return f"❌ Ping failed: {str(e)}"

def handle_inspect_command():
    try:
        mobo = subprocess.check_output(['sudo', 'dmidecode', '-s', 'baseboard-product-name'], text=True).strip()
        cpu = subprocess.check_output(['sudo', 'dmidecode', '-s', 'processor-version'], text=True).strip()
        return f"🕵️ *Minty Hardware Scan*\n🏗️ Mobo: {mobo}\n🧠 CPU: {cpu}"
    except Exception as e:
        return f"❌ Inspection failed: {str(e)}"

def handle_weather_command():
    try:
        # Uses your key: 97768e8378e893f4f2b1c271d62b8668
        url = f"http://api.openweathermap.org/data/2.5/weather?q={config.CITY_NAME}&appid={config.WEATHER_API_KEY}&units=metric"
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            data = response.json()
            temp = data['main']['temp']
            desc = data['weather'][0]['description']
            return f"🌡️ *Weather for {data['name']}*\nTemp: {temp}°C\nSky: {desc.capitalize()}"
        return "❌ Weather service temporarily unavailable."
    except Exception as e:
        return f"❌ Weather error: {str(e)}"

def handle_addtv_command(show_name):
    """Add a TV show to autodl-irssi filters"""
    try:
        autodl_cfg = os.path.expanduser("~/.autodl/autodl.cfg")
        
        # Create safe filter name (lowercase, underscores, no special chars)
        filter_name = show_name.lower().replace(" ", "_").replace("'", "").replace("&", "and")
        filter_name = ''.join(c for c in filter_name if c.isalnum() or c == '_')
        
        # Check if filter already exists
        with open(autodl_cfg, 'r') as f:
            if f"[filter {filter_name}]" in f.read():
                return f"⚠️ *TV Show Already Exists*\nShow: {show_name}\nFilter: {filter_name}"
        
        # Create new filter entry
        new_filter = f"""
[filter {filter_name}]
enabled=1
match-sites=tl
shows={show_name}
seasons=1-99
match-categories=TV - HD,TV
resolutions=720p,1080p,2160p
sources=WEB-DL,WEBDL,WEB,HDTV,BluRay
min-size=200MB
max-size=25GB
except-releases=*cam*,*ts*,*dubbed*,*.multi.*
upload-watch-dir=/home/martin/Downloads
"""
        
        # Append to config file
        with open(autodl_cfg, 'a') as f:
            f.write(new_filter)
        
        # autodl-irssi auto-detects config changes, no reload needed
        
        return f"📺 *TV Show Added Successfully!*\nShow: {show_name}\nFilter: {filter_name}\n✅ Monitoring started (autodl will detect in ~60s)"
        
    except Exception as e:
        return f"❌ addtv error: {str(e)}"

def handle_addmovies_command(movie_name):
    """Add a movie to autodl-irssi filters"""
    try:
        autodl_cfg = os.path.expanduser("~/.autodl/autodl.cfg")
        
        # Create safe filter name
        filter_name = movie_name.lower().replace(" ", "_").replace("'", "").replace("&", "and")
        filter_name = ''.join(c for c in filter_name if c.isalnum() or c == '_')
        
        # Check if filter already exists
        with open(autodl_cfg, 'r') as f:
            if f"[filter {filter_name}]" in f.read():
                return f"⚠️ *Movie Already Exists*\nMovie: {movie_name}\nFilter: {filter_name}"
        
        # Create new filter entry
        new_filter = f"""
[filter {filter_name}]
enabled=1
match-sites=tl
match-releases=*{movie_name}*
match-categories=Movies - HD,Movies
resolutions=1080p,2160p
sources=WEB-DL,WEBDL,WEB,BluRay
min-size=1GB
max-size=30GB
except-releases=*cam*,*ts*,*dubbed*,*.multi.*
upload-watch-dir=/home/martin/Downloads
"""
        
        # Append to config file
        with open(autodl_cfg, 'a') as f:
            f.write(new_filter)
        
        # autodl-irssi auto-detects config changes, no reload needed
        
        return f"🎬 *Movie Added Successfully!*\nMovie: {movie_name}\nFilter: {filter_name}\n✅ Monitoring started (autodl will detect in ~60s)"
        
    except Exception as e:
        return f"❌ addmovies error: {str(e)}"

def handle_seed_command(command):
    """Check seeding status or manage torrents"""
    try:
        download_dir = "/home/martin/Downloads"
        
        # Count .torrent files in watch directory
        torrent_files = []
        if os.path.exists(download_dir):
            torrent_files = [f for f in os.listdir(download_dir) if f.endswith('.torrent')]
        
        # Get directory size and file count
        total_size = 0
        file_count = 0
        
        if os.path.exists(download_dir):
            for root, dirs, files in os.walk(download_dir):
                file_count += len(files)
                for f in files:
                    try:
                        fp = os.path.join(root, f)
                        total_size += os.path.getsize(fp)
                    except:
                        pass
        
        size_gb = total_size / (1024**3)
        
        response = f"🌱 *Seed Status*\n"
        response += f"📂 Downloads: {file_count} files ({size_gb:.2f} GB)\n"
        response += f"🎯 Active Torrents: {len(torrent_files)}\n"
        
        if torrent_files:
            response += f"\n📥 *Recent Torrents:*\n"
            for torrent in torrent_files[:5]:  # Show first 5
                response += f"• {torrent[:40]}...\n" if len(torrent) > 40 else f"• {torrent}\n"
        
        return response
        
    except Exception as e:
        return f"❌ seed error: {str(e)}"
