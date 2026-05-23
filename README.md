# DJ Roomba

[![Python version](https://img.shields.io/badge/python-3.10%20to%203.13-blue.svg)](https://python.org)
[![GitHub license](https://img.shields.io/github/license/Jimgersnap/DJ-Roomba.svg)](LICENSE)

DJ Roomba is a Discord music bot written in [Python](https://www.python.org) 3.10–3.13, using the [discord.py](https://github.com/Rapptz/discord.py) library. It is a fork of [MusicBot](https://github.com/Just-Some-Bots/MusicBot) with additional commands, a cleaner visual style, and auto-deleting responses to keep your channels tidy. It plays requested songs from YouTube and other supported services, falls back to a configurable auto playlist when the queue is empty, and includes a permission system so owners can restrict commands to specific roles or users.

<!-- Screenshot placeholder: add a screenshot of DJ Roomba in action once available -->

## What's different from MusicBot

DJ Roomba started as a fork of MusicBot but has diverged in a few meaningful ways:

- **Auto-deleting responses** — DJ Roomba deletes its own messages after a short delay, keeping your channels clean rather than filling them with bot clutter.
- **Cleaner response style** — Responses use bold for song titles and names, backticks for channel names and command examples, and friendly first-person language with helpful command hints built in.
- **Additional commands** — DJ Roomba adds `promote`, `stop`, `reconnect`, `botinfo`, `nowplaying`, and `songprogress` on top of the MusicBot command set.
- **Activity status config** — You can configure the bot's Discord presence type (`playing`, `listening`, `watching`, `streaming`), status (`online`, `idle`, `dnd`, `offline`), and a streamer URL via `config/options.ini`.

## Requirements

- [Python](https://www.python.org) 3.10 or higher
- [FFmpeg](https://ffmpeg.org) — must be installed and available on your system PATH

## Setup

1. Create a bot application at the [Discord Developer Portal](https://discord.com/developers/applications) and copy your bot token.
2. Clone this repository:
   ```
   git clone https://github.com/Jimgersnap/DJ-Roomba.git
   cd DJ-Roomba
   ```
3. Install Python dependencies:
   ```
   pip install -r requirements.txt
   ```
4. Copy `config/example_options.ini` to `config/options.ini` and paste your bot token in the `Token` field.
5. Optionally copy `config/example_permissions.ini` to `config/permissions.ini` to customize permissions.
6. Start the bot:
   - Linux/macOS: `./run.sh`
   - Windows: `run.bat`

See [`config/example_options.ini`](./config/example_options.ini) for all available configuration options.

## Commands

DJ Roomba uses `!` as the default command prefix (configurable). Many commands have aliases — see [`config/example_aliases.json`](./config/example_aliases.json) for the defaults.

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
| `search <query>` | Search for a song and pick from results. |
| `shuffle` | Shuffle the queue. |
| `clear` | Clear the queue. |
| `remove <position>` | Remove a song from the queue by position. |

### Bot Control

| Command | Description |
|---|---|
| `summon` | Bring the bot to your voice channel. |
| `disconnect` | Disconnect the bot from voice. |
| `reconnect` | Reconnect the bot to voice, preserving the queue. |
| `autoplaylist` | Manage the auto playlist. |
| `clean` | Remove DJ Roomba messages from the channel. |
| `botinfo` | Show DJ Roomba version and info. |
| `perms` | Show your current permissions. |
| `help` | Show command help. |

## Permissions

Permissions are configured in `config/permissions.ini`. DJ Roomba ships with three example groups:

- **MusicMaster** — full access to all commands
- **DJ** — standard DJ controls, blacklisted from admin commands
- **Limited** — restricted to basic playback and queue viewing

## License

DJ Roomba is licensed under the [MIT License](LICENSE).  
Originally forked from [MusicBot](https://github.com/Just-Some-Bots/MusicBot) by Just-Some-Bots.
