# Private XHS wallpaper source relay

This small utility supports the current request without placing the shared XHS URL, access token,
or downloaded originals in the public repository. It runs the download step on a GitHub Actions
runner (which can reach XHS), then returns only an encrypted archive to the active branch. The
response private key stays outside the repository.

The note link is encrypted locally to the runner's public key before it is pushed. The runner
public key is generated on the first workflow run and published as `runner-public.pem`; its
private half is held in the runner's branch-scoped Actions cache. The response archive uses a
random AES-256-GCM key, which is separately wrapped to `result-public.pem`. Do not add either
private key, plaintext request, or extracted images to Git.

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

## Local checks

```sh
python -m unittest discover -s tools/xhs-wallpaper -p 'test_*.py'
```
