# DJ Roomba

[![Python version](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://python.org)
[![GitHub license](https://img.shields.io/github/license/Jimgersnap/DJ-Roomba.svg)](LICENSE)

DJ Roomba is a Discord music bot written in [Python](https://www.python.org) 3.10+, using the [discord.py](https://github.com/Rapptz/discord.py) library. It is a fork of [MusicBot](https://github.com/Just-Some-Bots/MusicBot) with additional commands, a cleaner visual style, and auto-deleting responses to keep your channels tidy. It supports both classic prefix commands and native Discord slash commands, plays requested songs from YouTube and other supported services (including Spotify), falls back to a configurable auto playlist when the queue is empty, and includes a permission system so owners can restrict commands to specific roles or users.

### Why "DJ-Roomba"?

DJ Roomba is Tom Haverford's invention from *Parks and Recreation* — a Roomba with an MP3 player strapped to it. As Tom put it: *"Little guy cruises around and plays music."* It first appeared in the Season 2 episode "Sweetums," rolling around his apartment and tearing it up, until Jerry stepped on it.

The name fits this bot on two levels. Like Tom's Roomba, it quietly cleans up after itself, automatically deleting its own messages so your channels stay uncluttered. And like the DJ part, it's there to keep the music going for everyone in the voice channel. It shows up, does its job, and leaves no mess behind.

<!-- Screenshot placeholder: add a screenshot of DJ Roomba in action once available -->

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

DJ Roomba uses `!` as the default command prefix (configurable with `setprefix`). Many commands have aliases — see [`config/example_aliases.json`](./config/example_aliases.json) for the defaults.

> **Slash commands:** Every command below is also available as a native Discord slash command (e.g. `/play`, `/queue`, `/nowplaying`), with argument hints and interactive buttons for browsing the queue and search results. Slash commands register automatically when the bot joins a server. The tables below use the prefix form, but the same commands work either way.

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
| `seek <time>` | Jump to a position in the current song (e.g. `1:30`). |
| `repeat [mode]` | Cycle through repeat modes: off, song, or queue. |
| `speed <0.5–2.0>` | Change playback speed. |
| `volume <0–100>` | Set the playback volume. |
| `move <from> <to>` | Move a queued song to a different position. |
| `shuffleplay <url or search>` | Add a song and immediately shuffle the queue. |

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
| `follow [@user]` | Have the bot follow you (or another user) between voice channels. |
| `karaoke` | Toggle karaoke mode — lowers music volume when someone speaks. |
| `autoplaylist` | Manage the auto playlist. |
| `clean` | Remove DJ Roomba messages from the channel. |
| `botinfo` | Show DJ Roomba version and info. |
| `perms` | Show your current permissions. |
| `help` | Show command help. |

### Utility

| Command | Description |
|---|---|
| `uptime` | Show how long the bot has been running. |
| `botlatency` / `latency` | Show response latency. |
| `botversion` | Show the bot version. |
| `checkupdates` | Check for bot and dependency updates. |
| `id [@user or #channel]` | Show the Discord ID of a user or channel. |
| `listids` | List IDs for all users and channels in the server. |

### Admin

These commands require elevated permissions (owner or configured permission group).

| Command | Description |
|---|---|
| `blockuser <@user>` | Block a user from using the bot. |
| `blocksong <url>` | Block a song or URL from being queued. |
| `setperms` | Manage user and role permissions. |
| `setalias <command> <alias>` | Create a command alias. |
| `setprefix <prefix>` | Change the command prefix. |
| `setname <name>` | Change the bot's username. |
| `setnick <nick>` | Change the bot's server nickname. |
| `setavatar <url>` | Change the bot's avatar. |
| `language <code>` | Set the bot's language. |
| `setcookies` | Update yt-dlp cookies for age-restricted content. |
| `config` | View or edit bot configuration. |
| `option` | Toggle bot options. |
| `cache` | Manage the audio cache. |
| `resetplaylist` | Reset the auto playlist to defaults. |
| `pldump` | Dump the current queue to a playlist file. |
| `restart` | Restart the bot process. |
| `shutdown` | Shut the bot down. |

## Permissions

Permissions are configured in `config/permissions.ini`. DJ Roomba ships with three example groups:

- **MusicMaster** — full access to all commands
- **DJ** — standard DJ controls, blacklisted from admin commands
- **Limited** — restricted to basic playback and queue viewing

## License

DJ Roomba is licensed under the [MIT License](LICENSE).  
Originally forked from [MusicBot](https://github.com/Just-Some-Bots/MusicBot) by Just-Some-Bots.
