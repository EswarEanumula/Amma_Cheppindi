# Run Amma Cheppindi on your Mac

## One-time installation

1. In GitHub, open **Settings → Actions → Runners → New self-hosted runner** in this private repository. Select macOS and ARM64. Run the setup commands shown by GitHub on your Mac. Add the custom label **amma-cheppindi** and install/start the runner service using the commands shown in the runner's instructions. Keep the Mac awake and connected at run time.
2. Install the tools in Terminal. These commands assume Homebrew is installed.

   ```sh
   brew install ffmpeg node@22 python
   brew install --cask font-noto-sans-telugu
   export PATH="/opt/homebrew/opt/node@22/bin:/opt/homebrew/bin:$PATH"
   npm install --global n8n@2
   mkdir -p ~/.amma-cheppindi
   chmod 700 ~/.amma-cheppindi
   /opt/homebrew/bin/python3 -m venv ~/.amma-cheppindi/venv
   ~/.amma-cheppindi/venv/bin/pip install edge-tts google-api-python-client google-auth-oauthlib
   ```

   FFmpeg must expose the ass filter.

3. In Google Cloud, enable YouTube Data API v3 and create a **Desktop app** OAuth client. Download the client file to **~/.amma-cheppindi/client.json**. Clone this repo on your Mac and run the following from its root.

   ```sh
   ~/.amma-cheppindi/venv/bin/python produce.py authorize
   ```

   Sign in to the YouTube channel you intend to use. Authorize while signed in as the same macOS user that runs the GitHub runner. The local token file stays on your Mac. Google consent configuration can limit refresh token lifetime, so check that your OAuth project is suitable for unattended use before enabling the schedule.

## Verify and enable

- After merging to the default branch, open **Actions → Telugu Shorts → Run workflow** and select **render**. Check the MP4 under **~/.amma-cheppindi/episodes/**. Listen for narration clarity and check Telugu glyphs.
- Run it again with **private**. Verify the channel, video and music in YouTube Studio.
- To publish new episodes automatically, set repository Actions variable **AMMA_DAILY_MODE** to **public** after verifying the private upload. The schedule is 13:17 UTC (6:47 PM India time). YouTube can return a different privacy status, which the job reports. Remove the variable to pause scheduled production.
- A completed upload is recorded locally by date. Changing modes on the same day will not upload a second copy or change the first video's visibility. If GitHub reports an ambiguous upload, check YouTube Studio. Clear the pending receipt only after confirming that the upload did not complete.

## Content and score

The renderer uses built-in Telugu stories, stylized illustrated backgrounds, and generated Telugu narration via edge-tts, which requires network access. The instrumental score is synthesized locally from a short original motif and mixed beneath the narration. The initial three stories repeat in rotation. Edit STORIES in produce.py to expand the catalog. Generated files and OAuth credentials stay outside the checkout.
