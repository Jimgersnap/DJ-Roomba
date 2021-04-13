import os.path
import subprocess

MAIN_VERSION = '1.9.8_4'
SUB_VERSION = ' - 1.3.0a'
VERSION = MAIN_VERSION + SUB_VERSION

#try:
#  VERSION = subprocess.check_output(["git", "describe", "--tags", "--always"]).decode('ascii').strip()
#except Exception:
#  VERSION = 'version_unknown'

AUDIO_CACHE_PATH = os.path.join(os.getcwd(), 'audio_cache')
DISCORD_MSG_CHAR_LIMIT = 2000
