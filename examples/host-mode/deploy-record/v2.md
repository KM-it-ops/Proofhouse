# Putting the Tidewatch site online

The site is two files, `index.html` and `style.css`, in `examples/host-mode/site`. `proofhouse deploy` hands that folder to a hosting tool's own command line. Nothing is uploaded until you run the real command.

## 1. See the exact command first (no account, no network)

```bash
proofhouse deploy examples/host-mode/site --to netlify --dry-run
```

It prints one line, `netlify deploy --dir <folder> --prod`, and runs nothing. Swap `--to` for `vercel`, `cloudflare` (also pass `--name tidewatch`, the Pages project name) or `surge` (the site becomes `tidewatch.surge.sh`). `proofhouse deploy --list` shows all four.

## 2. What the real run needs

| Target | Install the tool | Key the tool reads from your environment |
|--------|------------------|--------------|
| netlify | `npm install -g netlify-cli` | `NETLIFY_AUTH_TOKEN` |
| vercel | `npm install -g vercel` | `VERCEL_TOKEN` |
| cloudflare | `npm install -g wrangler` | `CLOUDFLARE_API_TOKEN` |
| surge | `npm install -g surge` | `SURGE_TOKEN` |

Leave `--dry-run` off to deploy. If the tool is missing, Proofhouse stops and prints the install line instead of guessing. Every real run, passed or failed, appends one line to `deploys.jsonl` in the Proofhouse home with the target, folder, command, address and exit code.

## 3. When it stops early

- Folder has no `index.html`: `has no index.html to deploy`.
- Unknown target: the error lists the four known ids.
- Target name with capitals or spaces: `--name must be lowercase letters, digits and hyphens`.
