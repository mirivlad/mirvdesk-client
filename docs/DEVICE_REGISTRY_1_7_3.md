# MirvDesk Client 1.7.3 — device inventory

MirvDesk now reports host identity to its own self-hosted server without requiring account login. After service startup, the host sends an Ed25519-signed heartbeat once per minute using its existing rendezvous signing key. The server matches this key against its local HBBS peer table and requires a fresh, single-use challenge.

Only the host service reports presence; GUI login sessions do not each create a separate host heartbeat. This does not enable remote control or bypass local connection approval/passwords.

Settings → Account → Administration → Devices includes:

- All devices (server-wide, registered by HBBS or account login);
- My devices (linked to the MirvDesk account);
- Accessible to me (personal devices plus group grants);
- search by peer ID, hostname, display name, owner or group;
- online/offline/unknown presence filtering and last verified heartbeat time;
- admin-defined display name, distinct from reported hostname;
- OS, architecture, version, notes and group assignments when available.

The server must support the device-registry-v1 capability (MirvDesk Server 1.7.3 development). An old server continues to handle remote control and account logins, but will not accept the new heartbeat or display-name endpoint.

Important: Groups grant visibility in Accessible devices, not transport-layer authorization. A device discovered without a login has no account owner and is initially unassigned. Presence is unknown for pre-1.7.3 clients until they transmit a signed heartbeat.

This branch needs a full cross-platform native CI run and live integration testing before a 1.7.3 release is published.