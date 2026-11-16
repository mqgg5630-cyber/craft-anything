# Requested wallpaper delivery — blocked before download

Source: https://xhslink.cn/o/AgiCwSCgdwL

Title: 奶fufu淡蓝手绘｜氛围感手机壁纸

Note ID: `6ad631d1000000002803bf27`. Public page lists seven images.

## Verified on 2026-11-16

- Resolved the share URL and extracted seven distinct public image tokens.
- Inspected the file trees of all 15 branches of the user-provided reference repository. No source code or assets were copied.
- Direct CDN access fails in the restricted sandbox.
- GitHub rejected a push containing a new Actions workflow because the current GitHub App lacks `workflows` permission. No remote workflow was installed or executed.
- **Zero source files downloaded; zero generated wallpapers; zero UI previews. This is not a completed delivery.**

`download.py` is an original, job-specific downloader, not a general note parser or an integrated application tool. It tries three public CDN variants per image, validates decoded images, chooses the largest available pixel dimensions (then byte size), preserves response bytes, and records dimensions, byte sizes and SHA-256 values. Limits: 12 MiB per response, 75 MiB per job, 35 seconds per request, seven fixed image tokens. It does not authenticate or bypass private access. Public CDN files cannot be guaranteed to be the author's master files. The author notes that master files are shared separately in a group.

## Resume with network access

1. Install Python 3.12 and `Pillow==11.3.0` in a virtual environment.
2. On a machine with CDN access: `python tools/wallpaper-job/download.py` from the repository root.
3. Alternatively, after the GitHub connection has permission to write workflows, install `workflow.yml.example` as `.github/workflows/wallpaper-download.yml` and push on the existing session branch. The workflow returns the downloaded files to that same branch. It intentionally contains no cookies or credentials.
4. Inspect every downloaded image and `下载记录.json` before creating image-conditioned prompts. Do not generate from the title alone and describe the output as an image-based recreation.
5. Generate ten independent clean images, keeping the source references and prompts recorded. Add phone UI as a separate deterministic overlay, never as part of the clean image prompt.
6. Validate counts and images and package these distinct folders:

```text
blue-kitty/
  01-下载原图/           # seven unchanged downloaded files + download record
  02-复刻无手机UI/       # ten independently generated images
  03-复刻有手机UI/       # ten matching overlays
  04-说明与验收/         # provenance, generation prompts, dimensions, counts
```

The generation, overlay and packaging steps have not been implemented or run yet. Third-party character artwork should not be represented as owned original IP; label generated results as AI-generated.

Run offline downloader regression tests with `python -m unittest discover -s tools/wallpaper-job -p 'test_*.py'`.
