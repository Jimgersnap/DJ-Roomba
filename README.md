# DJ Roomba

[![Python version](https://img.shields.io/badge/python-3.10%20to%203.13-blue.svg)](https://python.org)
[![GitHub license](https://img.shields.io/github/license/Jimgersnap/DJ-Roomba.svg)](LICENSE)

DJ Roomba is a Discord music bot written in [Python](https://www.python.org) 3.10–3.13, using the [discord.py](https://github.com/Rapptz/discord.py) library. It is a fork of [MusicBot](https://github.com/Just-Some-Bots/MusicBot) with additional commands, a cleaner visual style, and auto-deleting responses to keep your channels tidy.

DJ Roomba plays requested songs from YouTube and other supported services into a Discord voice channel. When the queue is empty, it can automatically play from a configurable auto playlist. A permission system lets server owners restrict commands to specific roles or users.

## Setup

1. Install [Python](https://www.python.org) 3.10 or higher.
2. Clone this repository.
3. Run `pip install -r requirements.txt` to install dependencies.
4. Copy `config/example_options.ini` to `config/options.ini` and fill in your bot token.
5. Copy `config/example_permissions.ini` to `config/permissions.ini` if you want custom permissions.
6. Run the bot with `./run.sh` (Linux/macOS) or `run.bat` (Windows).

See [`config/example_options.ini`](./config/example_options.ini) for all available configuration options.

## Commands

DJ Roomba uses `!` as the default command prefix (configurable). Below are the available commands.

### Playback

| Command | Description |
|---|---|
| `play <url or search>` | Add a song to the queue. |
| `playnow <url or search>` | Play a song immediately, skipping the current track. |
| `playnext <url or search>` | Add a song to the front of the queue. |
| `promote <position>` | Move a queued song to the front of the queue. |
| `stream <url>` | Stream live media directly (no download). |
| `skip` | Vote to skip the current song, or force-skip if you have permission. |
| `stop` | Stop playback and clear the queue. |
| `pause` | Pause playback. |
| `resume` | Resume paused playback. |
| `volume <0–100>` | Set the playback volume. |

### Queue

| Command | Description |
|---|---|
| `queue` | Show the current song queue. |
| `np` / `nowplaying` / `songprogress` | Show the currently playing song with progress. |
| `shuffle` | Shuffle the queue. |
| `clear` | Clear the queue. |
| `remove <position>` | Remove a song from the queue by position. |

### Bot Control

| Command | Description |
|---|---|
| `summon` | Bring the bot to your voice channel. |
| `disconnect` | Disconnect the bot from voice. |
| `reconnect` | Reconnect the bot to voice, preserving the queue. |
| `botinfo` | Show DJ Roomba version and info. |
| `help` | Show command help. |

### Other

| Command | Description |
|---|---|
| `search <query>` | Search for a song and pick from results. |
| `autoplaylist` | Manage the auto playlist. |
| `perms` | Show your current permissions. |
| `clean` | Remove DJ Roomba messages from the channel. |

Many commands have aliases. See [`config/example_aliases.json`](./config/example_aliases.json) for the defaults.

## Permissions

Permissions are configured in `config/permissions.ini`. DJ Roomba ships with three example groups:

- **MusicMaster** — full access to all commands
- **DJ** — standard DJ controls, blacklisted from admin commands
- **Limited** — restricted to basic playback and queue viewing

## License

DJ Roomba is licensed under the [MIT License](LICENSE).  
Originally forked from [MusicBot](https://github.com/Just-Some-Bots/MusicBot) by Just-Some-Bots.
