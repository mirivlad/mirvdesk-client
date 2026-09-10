# MirvDesk roadmap

This roadmap covers both the client and the companion `mirvdesk-server`. Version boundaries are targets, not promises, but the architectural rules below are intended to be stable.

## v1.6.0 — self-hosted baseline

- mandatory `MIRVDESK_SERVER_URL` with no project-wide default server;
- isolated MirvDesk application identity and packaging;
- distinct MirvDesk visual palette;
- account login and personal address-book synchronization;
- RustDesk-compatible Accessible devices / Groups view;
- server-side users, registered devices and basic group access;
- Fast / Full / Release CI split.

The 1.6 group implementation is deliberately a baseline. Its current single-group-per-device storage must **not** become a permanent public contract.

## v1.7.0 — administration console

The primary administration UI should live inside the MirvDesk desktop client. A logged-in user receives server-side capabilities; users with administration rights see an additional **Administration** / **Devices and groups** menu item. Ordinary users do not see it.

The administration window should provide one coherent UI for devices, groups and users. It is a client for a server-side admin API; business rules and authorization stay on the server.

### Device registry

Each registered device should expose enough information to identify it safely:
- stable MirvDesk device ID / RustDesk peer ID;
- reported device/host name;
- administrator-defined display name kept separately from the reported name;
- owner account;
- operating system and architecture;
- MirvDesk client version;
- last-seen time and online/offline state where available;
- optional administrator note.

An administrator-visible name must never overwrite the machine-reported identity. A UI should be able to show, for example, `Касса №2` together with `KASSA-PC02 · Windows 10 · 123456789`.

### Many-to-many groups

Both sides of group membership are many-to-many:

- one user may have access to several groups;
- one group may be visible to several users;
- one device may belong to several groups;
- one group may contain several devices.

The server therefore needs a schema migration from the 1.6 transitional `devices.group_id` model to a join table for device/group membership. The existing user/group join table may remain if its semantics fit the final model.

The effective Accessible devices list is the union of devices reachable through every group granted to the current user, plus any explicitly defined ownership rule. Duplicate devices must collapse to one entry.

### Administration operations
The first administration console should support:

- create, rename and delete groups;
- assign/remove devices to/from any number of groups;
- grant/revoke user access to any number of groups;
- set a device display name and administrator note;
- inspect device identity, owner, platform, version and last-seen state;
- create users and perform safe account-management operations already supported by the server;
- refresh/synchronize without restarting the client.

Server authorization is authoritative. Hiding a menu item in Flutter is UX, not a security boundary.

## v1.7.x — delegated permissions and polish

Do not hard-code the UI around one `is_admin` boolean. The server should be able to expose capabilities such as:

- `manage_users`;
- `manage_groups`;
- `manage_devices`;
- `view_all_devices`.

Initially the administrator may simply receive all capabilities. The capability model leaves room for a site/group administrator later without redesigning the API or UI.

Bulk operations, search/filtering, clearer online state and audit information can be added incrementally after the basic console is stable.

## v1.8+ — optional web administration
A web admin UI is a later option, not the primary management surface. If implemented, it must reuse the same server admin API and authorization model as the desktop administration console; it must not become a second source of business rules.

Potential later work also includes shared address books/profiles and a MirvDesk-specific update channel.

## Upstream compatibility is an architectural requirement

MirvDesk is a RustDesk downstream, not a clean-room rewrite. Long-term ability to absorb useful upstream RustDesk changes is more valuable than cosmetic source-level purity.

Every feature in this roadmap must follow [UPSTREAM_COMPATIBILITY.md](UPSTREAM_COMPATIBILITY.md). In particular:

- keep RustDesk transport/protocol and remote-control engine changes to the minimum necessary;
- prefer additive MirvDesk code and adapters over rewriting upstream modules;
- keep MirvDesk-only API operations in a MirvDesk namespace so they do not collide with future upstream endpoints;
- retain upstream-compatible endpoints/response shapes where MirvDesk intentionally implements an upstream feature such as Accessible devices / Groups;
- negotiate optional MirvDesk behavior through server discovery/capabilities instead of assuming every server supports it;
- keep branding/theme/application-identity patches centralized;
- avoid renaming internal crates, ABI symbols or libraries merely for cosmetic branding when doing so increases merge cost;
- preserve graceful operation against an older MirvDesk server: unsupported optional features should disappear or degrade, not break the rest of the client.

When compatibility and a MirvDesk-specific feature conflict, document the divergence explicitly before implementing it.