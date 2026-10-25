# my-sub-nodes starter

This package builds a Base64-encoded proxy URI subscription from source URLs, optionally checks TCP endpoint reachability, and can publish the result to Cloudflare Workers KV for a stable HTTPS subscription endpoint.

## Important security note

The repository you linked is public. Do **not** commit subscription URLs, proxy credentials, UUIDs, Cloudflare API tokens, or your private subscription output. Put source URLs and API credentials in GitHub Actions **Secrets**. The Worker URL contains a bearer token: anyone who gets that URL can read the subscription, so keep it private and rotate it if exposed.

## 1. Add the files to your GitHub repository

Upload the contents of this package to `https://github.com/antioxi1/my-sub-nodes` using **Add file → Upload files**, or push them with Git.

## 2. Configure the source URLs

In the repository, open **Settings → Secrets and variables → Actions → New repository secret**.

Create `SUBSCRIPTION_URLS`. Its value should contain one subscription URL per line. Do not use a public repository file to store these URLs if they contain private access tokens.

## 3. Run a test update

Open **Actions → Update proxy subscription → Run workflow**. The scheduled workflow runs every six hours at minute 17 UTC, although GitHub can delay scheduled runs. The workflow log reports the number of candidate links and output links.

This workflow only creates local job output unless the Cloudflare secrets below are configured. GitHub Actions artifacts are not a permanent subscription host.

## 4. Optional: publish a stable HTTPS subscription with Cloudflare

1. Create a Cloudflare Workers KV namespace.
2. Copy its namespace ID.
3. In `worker/wrangler.toml`, replace `REPLACE_WITH_YOUR_KV_NAMESPACE_ID` with that ID.
4. Deploy the Worker from the `worker` directory using Wrangler, or create a Worker in the Cloudflare dashboard and paste `worker/index.js`.
5. Bind the KV namespace to the Worker with binding name `SUBSCRIPTIONS`.
6. Add a Worker secret named `SUB_TOKEN` containing a long random token. Do not put this token in the repository.
7. In GitHub repository Actions secrets, add:
   - `CLOUDFLARE_API_TOKEN` — a narrowly scoped API token with permission to write to the chosen Workers KV namespace.
   - `CLOUDFLARE_ACCOUNT_ID` — your Cloudflare account ID.
   - `CF_KV_NAMESPACE_ID` — the same KV namespace ID.
8. Run the workflow again.

Your subscription URL will be:

`https://YOUR-WORKER.YOUR-SUBDOMAIN.workers.dev/YOUR_SUB_TOKEN/subscription.txt`

The response body is Base64-encoded proxy URI lines. Try importing it in Loon or Shadowrocket as a remote subscription. Client support depends on the actual URI protocols and parameters in your source feeds.

## What the TCP check does—and does not do

The check tests whether the node's endpoint TCP port can be reached from GitHub's runner. It does **not** prove that the proxy authentication works, that traffic can pass through it, that the IP is clean, or that the node is safe. Some URI formats do not expose a directly parseable endpoint; those links are retained rather than automatically discarded.

## Supported URI prefixes

`ss://`, `vmess://`, `vless://`, `trojan://`, `socks://`, `socks5://`, `http://`, and `https://`.

This starter does not generate a Clash YAML configuration. A valid Clash configuration requires protocol-specific parsing and compatibility handling; using a URI list as if it were Clash YAML would produce an invalid config.
