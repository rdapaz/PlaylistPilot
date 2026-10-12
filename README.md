# PlaylistPilot

Desktop app (Python + PySide6) that builds genre and custom playlists for portable music players and writes them where each player expects them, in the exact path form that player resolves.

Built-in device profiles, verified on the real hardware:

| Player | Reach it via | Playlist entries | Dropped into |
|---|---|---|---|
| FiiO M33 R2R | FTP, port 2100 (foobar2000 mobile) | `/storage/external_sd/music/...`, `/storage/emulated/0/Music/...` | SD music root and `foobar2000 Music Folder` |
| iBasso DX180 | FTP, port 2100 | `/storage/<SD volume ID>/music/...`, `/storage/emulated/0/Music/...` | same |
| Shanling M0 Pro | USB drive (`D:\`) | `A:\music\...` with backslashes, `.m3u` | `_explaylist_data`, then Import Playlist on the player |
| iPhone | FTP, port 21 | relative to `foobar2000 Music Folder` (percent-encoded names decoded) | `foobar2000 Music Folder` |

The SD volume ID shows in foobar2000 mobile under a track's Properties > Location (for example `1A2B-3C4D:music/...`, so the prefix is `/storage/1A2B-3C4D/music/`).

## Configure your players

Copy `devices.example.json` to `devices.json` (next to `main.py`) and put in your players' real
addresses, usernames, SD volume IDs and drive letters. `devices.json` is git-ignored, so your LAN
details never leave your machine; the example file ships with placeholder addresses. Profiles can
also be added or edited inside the app (Device > Add / Edit); those are stored in
`~/.playlistpilot/devices.json` and override the file next to `main.py` by name.

## Run

```bash
pip install -r requirements.txt
python main.py
```

## Flow

1. **Device**: choose a player, follow the guidance, enter the FTP password (or confirm the drive), Test connection, Scan library.
2. **Library**: check how tracks were classified; double-click an artist to set its playlists.
3. **Playlists**: tick genre playlists and/or compose custom ones. Optionally let Claude suggest genres for artists no rule covers (key in Settings or `ANTHROPIC_API_KEY`).
4. **Deploy**: copies go to `<playlist folder>\<device>\` and to every deploy folder on the player.
5. **Soundiiz**: open a Soundiiz CSV export, review the fuzzy matches against the device library, fix any by hand, queue it as a playlist and deploy. Export built playlists (or an existing .m3u8) as Soundiiz-format CSV for the trip back to a streaming service.

## Layout

```
main.py                 entry point
core/profiles.py        DeviceProfile + built-in players, persisted to ~/.playlistpilot/devices.json
core/library.py         FTP / local scanning, artist-album-title inference, listing files
core/genres.py          artist and album rules, Claude classifier, overrides and cache
core/playlists.py       m3u rendering, local copies, deploy (FTP STOR with size check / USB write)
core/settings.py        QSettings wrapper
gui/                    theme, main window, views (device, library, playlists, settings), dialogs, widgets
```
