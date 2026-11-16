# Private XHS wallpaper source relay

This small utility supports the current request without placing the shared XHS URL, access token,
or downloaded originals in the public repository. It runs the download step on a GitHub Actions
runner (which can reach XHS), then returns only an encrypted archive to the active branch. The
response private key stays outside the repository.

The note link and any browser-extracted image URLs are encrypted locally with a fresh AES-256-GCM
key; only that random key is wrapped to the runner's public key before the encrypted request is
pushed. The runner public key is generated on the first workflow run and published as
`runner-public.pem`; its private half is held in the runner's branch-scoped Actions cache. The
response archive uses a separate random AES-256-GCM key, wrapped to `result-public.pem`. Do not
add either private key, plaintext request, or extracted images to Git.

The fetcher reads the note's `urlDefault`/`urlPre` image entries, tries the source CDN/original
variants plus the signed page image, validates actual image bytes/dimensions, and writes a
structured source folder and metadata. Any image that cannot be fetched is recorded as failed;
a successful HTTP response alone is not counted as a successful download.

## Output layout after local decryption

```text
01-原图/
  01.png ... NN.png
  note.json
  README.txt
```

Generated wallpaper artwork is deliberately kept in a separate results folder. The UI preview is
a deterministic derivative of each clean artwork, never baked into the wallpaper image itself.

After placing exactly ten generated images in an artwork folder, create both output variants with:

```sh
python tools/xhs-wallpaper/render_set.py /path/to/art /path/to/02-结果
```

This produces 10 portrait PNG wallpapers in `无手机UI/`, 10 corresponding JPG lock-screen
previews in `手机UI预览/`, and a versioned `manifest.json`. The default preview date/time can be
overridden using `--date` and `--time`.

## Local checks

```sh
python -m unittest discover -s tools/xhs-wallpaper -p 'test_*.py'
```
