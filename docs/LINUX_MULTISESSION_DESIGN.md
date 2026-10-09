# Linux multi-session routing — MirvDesk 1.7 design

Status: **design and discovery only**. Do not enable remote selection of
non-served graphical sessions until the routing and capture path exists.

## Requirements

1. One public rendezvous ID for a host. `<id>\\<os-user>` is a hint for
   selecting the target OS session, not a MirvDesk API account.
2. Selecting user/session B must not interrupt a connection to user/session A.
3. Normal host authorization (temporary/permanent password, click approval,
   2FA, deny rules) must complete before assigning the connection to B.
4. On unavailable/ambiguous sessions, fail closed. Never show seat0 as a
   fallback to a requested different account.
5. X11 and Wayland may require different capture and input methods;
   especially, never bypass a Wayland compositor/portal consent decision.
6. Work under root daemon installed mode, without creating a second hbbs
   registration for the same host ID. Normal standalone mode remains intact.

## Existing architecture

- `src/platform/linux.rs::start_os_service()` watches the **active seat0**
  and owns a single `user_server` child. It kills/replaces that child when
  the user/display changes.
- `src/platform/linux.rs::try_start_server_()` starts the user child with
  DISPLAY, XAUTHORITY, WAYLAND_DISPLAY, DBUS and HOME.
- `src/server.rs::start_server()` starts `RendezvousMediator::start_all()`
  and the common IPC listener, so simply launching multiple copies is not
  independent: rendezvous identity and IPC naming clash.
- `src/server/connection.rs` performs connection authentication, chooses
  capture/audio/input services, and sends `PeerInfo`.
- `src/platform/linux_sessions.rs` now provides **read-only** logind
  discovery. The host advertises `linux_logind_sessions_json` in
  `PeerInfo.platform_additions`. This inventory is advisory: `startx`
  sessions may still be typed as tty by logind.

## Proposed service split

```
 Remote client
     |
 hbbs / hbbr (unchanged rendezvous ID)
     |
 Host connection broker (one, host-owned)
     |-- verify host password / approval / 2FA
     |-- resolve user + optional logind session ID
     |-- pin connection to exact (UID, logind SID)
     |
     +--- session worker (UID=1000, logind SID=3) -- X11 capture/input
     |
     +--- session worker (UID=1001, logind SID=6) -- Wayland/PipeWire
```

The broker retains the rendezvous connection, ID, cryptographic handshake,
and host authentication. Workers **must not** start another
`RendezvousMediator` or own the same IPC endpoint. They run under the
selected user's UID with independently scoped Unix sockets (using session
ID as well as UID), and only process broker-authorized operations.

The broker maps an authorized connection to one immutable target session.
Each worker attaches to its own display compositor, captures frames and
accepts permission-checked input for only that session. Worker termination
closes only the connections pinned to it. A failed worker must not switch
the global seat or fall back to another user's screen.

## Work order

1. Read-only inventory with typed parser, filtering, tests and UI metadata
   (**implemented in PR #11**).
2. Introduce a session-keyed registry and per-session IPC endpoint names,
   without changing the active-seat capture path.
3. Decouple rendezvous / remote-connection ownership from graphical capture
   helpers. Preserve existing single-session behavior as fallback.
4. Support explicit X11 session routing, with a fixture having two active
   X servers and simultaneous remote connections.
5. Add Wayland workers with correct DBus session bus, PipeWire capture,
   portal consent and input injection only where supported.
6. Present a session selector when the requested OS account has more than
   one graphical session. Remember the selected **session ID** for the
   connection, not merely the username.
7. Verify lifecycle: logout, session lock, greeter, Fast User Switching,
   hotplug, disconnect, reconnection, same-user multi-session,
   concurrent users, and crashes.

## Compatibility & security

- Hosts lacking the new worker capability must reject non-served explicit
  targets; the existing client may connect normally by plain ID.
- `loginctl` enumeration is **not** authorization, and an OS username is
  not proof of ownership. Existing host consent/password still governs.
- A logind session is an ephemeral runtime object, not a new long-lived
  rendezvous ID or MirvDesk API account.
- If a target session logs out, close connections pinned to that SID. Do
  not redirect them to a new session for the same username automatically.
- Do not advertise full Linux multi-session support until native Linux
  builds and real multi-session X11 + Wayland tests pass.
