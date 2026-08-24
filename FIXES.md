HMB GLOBAL — FIXED BUILD

Main fixes:
- /seek now defers immediately, downloads in a worker thread, and uses followup.send().
- /seek no longer lets the old voice callback start the next song.
- /skip correctly skips the requested number of songs.
- /stop invalidates the old playback callback before disconnecting.
- Playback callbacks are generation-safe, preventing duplicate/incorrect next-song starts.
- YouTube downloads use robust final-file detection, including post-processing filename changes.
- Failed downloads put the song back into the queue instead of silently losing it.
- /play and /playtop move YouTube searching off the Discord event loop.
- Deno is passed to yt-dlp explicitly by executable path.
- Temporary audio files are cleaned up safely.
- The accidental duplicated nested discord-main project was removed from this clean package.

Validation:
- main.py compiles successfully.
- Project test suite: 6 tests passed.
- Slash-command count remains exactly 100.

Deployment:
1. Upload/extract this project as the Fly.io app source.
2. Redeploy from the project root so Fly builds this main.py.
3. Confirm logs show the bot starts and Deno/cookie diagnostics.
4. Test /play, /skip, /stop, and /seek 30 in Discord.
