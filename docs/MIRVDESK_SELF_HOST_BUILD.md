# Building MirvDesk for your own server

MirvDesk is a **self-hosted** remote desktop project. This repository contains the client; the server is maintained separately at [mirivlad/mirvdesk-server](https://github.com/mirivlad/mirvdesk-server).

MirvDesk intentionally has **no public or project-wide default server**. Before compiling the client you must deploy your own MirvDesk Server and set the client bootstrap URL in `MIRVDESK_SERVER_URL`.

## GitHub Actions

Create a repository variable in your fork:

1. Open **Settings → Secrets and variables → Actions → Variables**.
2. Create `MIRVDESK_SERVER_URL`.
3. Set it to the public base URL of your own MirvDesk Server, for example `https://desk.example.com`.
4. Run the build or push a release tag.

This is a repository **variable**, not a secret: the URL is embedded in the client binary by design. Do not put credentials or tokens in it.

## Local builds

Export the same variable before invoking Cargo or `build.py`:

```sh
export MIRVDESK_SERVER_URL="https://desk.example.com"
cargo build --release
```

The build fails if `MIRVDESK_SERVER_URL` is missing, empty, or does not start with `http://` or `https://`. There is no fallback to the MirvDesk author's infrastructure.

At first launch the client requests `/.well-known/mirvdesk` from that base URL and discovers the ID server, relay server, API URL and public key. Release CI also checks Linux packages to ensure the configured bootstrap URL was actually embedded.

## Server capabilities

The discovery document can advertise optional server capabilities. MirvDesk 1.6 uses the `groups` capability to enable the **Accessible devices / Groups** tab only when the connected MirvDesk Server actually supports the required APIs. Older servers continue to work for remote control, accounts and the personal Address Book; the Groups UI stays hidden until the server is upgraded.

For MirvDesk 1.6 Groups, use an up-to-date build of [mirivlad/mirvdesk-server](https://github.com/mirivlad/mirvdesk-server).
