# PlaylistPilot help

## Device

Pick the player you want to work with. The guidance box explains how to make it reachable: foobar2000 mobile players expose an FTP server (Tools > FTP Server) that only runs while the screen is awake; drive-based players such as the Shanling M0 Pro mount as a drive letter over USB.

- **Test connection** logs in (FTP) or checks the drive and music folder (USB). Folders the server shows that are not in the profile are reported so you can add them as volumes.
- **Scan library** walks every volume and lists all audio files. Over FTP this takes a few minutes for 10,000 files. The listing is saved beside the playlist copies so **Load last listing** can rebuild without the player.
- **Read tags** (USB only) opens each file with mutagen to read artist, album and genre tags instead of inferring them from folder names. Slower but more accurate.
- **Add / Edit / Delete** manage device profiles. Deleting a built-in profile resets it to its defaults.

A profile records where the music lives (volumes), what to put in front of each path in a playlist (prefix), where playlists are dropped (deploy folders) and the file format. The built-in profiles use conventions verified on the real players:

- FiiO M33 R2R and iBasso DX180: absolute Android paths such as `/storage/external_sd/music/...` and `/storage/emulated/0/Music/...`, `.m3u8`, dropped in both the SD music root and `foobar2000 Music Folder`.
- Shanling M0 Pro: `A:\music\...` with backslashes, `.m3u`, dropped in `_explaylist_data`, then imported on the player.
- iPhone: paths relative to `foobar2000 Music Folder`, with percent-encoded names decoded.

## Library

Every scanned track with the artist and album inferred from its folders and the playlists it currently lands in. Filter by text, genre or volume.

- **Source** shows where the genre came from: `rule` (built-in artist map), `claude` (a cached Claude suggestion) or `manual` (your override).
- Double-click a row, or select it and press **Set genres for selected artist**, to choose the playlists an artist belongs in. Overrides are saved and win over everything else.

## Playlists

Two ways to build:

- **Genre playlists**: tick the ones you want. Counts come from the artist rules, album rules, Claude's cached answers and your overrides.
- **Custom playlist**: filter the library, add tracks (double-click or the buttons), order them by dragging, name the list and press **Add to build list**.

If artists are left unplaced, **Ask Claude about unknown artists** sends their names and a few album titles to the model chosen in Settings and caches the answers. Review or forget them with **Review Claude's answers**; override individual artists in Library.

- **Preview** shows the first lines of each playlist exactly as they will be written.
- **Save copies locally** writes the playlists under the folder set in Settings, in a sub-folder named after the device.
- **Deploy to device** saves the local copies and then writes every playlist into each deploy folder of the device, verifying the size over FTP. For USB players, eject the drive afterwards and import the playlists on the player.

## Soundiiz

Soundiiz exports any streaming playlist as a CSV (Track name, Artist name, Album, Playlist name, Type, ISRC, Duration). The rows carry no file paths, so PlaylistPilot matches each one against the scanned library of the current device.

- **Open CSV** reads the export and matches every row on title and artist, with album as a tie-breaker. Scores below **Min score** count as unmatched; raise it for stricter matching.
- Rows are coloured: green matched, red unmatched, amber score means a match worth checking. **Double-click** a row (or press Fix selected match) to search the library and pick the right track, or leave it unmatched.
- **Save unmatched as CSV** writes the rows that are not on the device, in Soundiiz format, so you can see what to copy over.
- **Add matched tracks to build list** queues the result as a custom playlist under the chosen name. Deploy it from the Playlists view like any other playlist.

Export goes the other way: select built genre or custom playlists and press **Export selected** to write one CSV per playlist in Soundiiz's column layout, ready for soundiiz.com > Import > CSV. **Export an .m3u8 file** converts an existing playlist file using its track labels.

## Settings

- **Folder** for local copies and file listings (defaults to `X:\music\playlists` when that share is mapped).
- **API key** and **model** for the optional Claude classification. Leave the key empty to use the `ANTHROPIC_API_KEY` environment variable.

## Troubleshooting

- `WinError 10061` or connection refused: the FTP server stopped because the player's screen locked. Wake it and retry.
- A playlist opens on the player but nothing plays: the path prefix is wrong for that player. Edit the device and check the volume prefixes against a track's Properties > Location in foobar2000 mobile.
- Tracks from the iPhone look like `%e2%ad%90`: enable the percent-decoding option in the device profile and rescan.
