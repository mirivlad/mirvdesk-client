# OS desktop session addressing (1.7 preview)

MirvDesk API accounts control personal address books, groups and admin access.
They are **not** the operating-system accounts of remote hosts.

## Address grammar

- `123456789` — normal connection, unchanged.
- `123456789\vasya` — target OS user `vasya` on host `123456789`.
- `123456789@other-server\petya` — explicit alternate rendezvous host.
- To store shortcuts in an address book, store the whole address. Only the ID
  preceding the final backslash is used for rendezvous.

The suffix does **not** authenticate or grant access to another user's desktop.
Normal remote-host password/approval and permission checks still apply.

## Windows

The existing WindowsSessions/SelectedSid protocol is reused. Where the host
advertises several sessions and exactly one matches the requested account,
it is selected automatically. When several sessions match, the existing session
picker appears, filtered to that OS account. If none match, the client rejects
the requested target rather than falling through to an unrelated session.

This depends on the remote installed service exposing RDP sessions; without
that capability only the currently served Windows desktop is available.

## Linux: current limitations and next implementation step

The current Linux root service launches a **single** user `--server` instance
for the active seat0 session and changes that instance on desktop switching.
A target suffix matching that user works. A different user is explicitly
rejected (including by the patched Linux host) rather than showing another
user's desktop.

**Parallel Linux sessions are not implemented yet.** Implementing them requires
a root service that enumerates logind sessions and can route each authenticated
remote connection to a stable per-session helper without killing or replacing
the helpers for other sessions. Both X11 and Wayland need independent
screen/input backends. For Wayland, capture/remote input must obey the session
compositor and portal permissions; copying DISPLAY between processes is
insufficient. Do not claim arbitrary-user Linux routing until that is in place
and integration-tested on multi-seat/multi-session installations.

The host target is carried as an OSLogin username-only hint in the existing
RustDesk protocol message, with **no OS password**, to avoid changing the
hbb_common protobuf submodule. The target is included in the login scope digest
so it cannot be silently switched between authentication retries.

## Random ID

The desktop Change ID dialog provides a **Generate new ID** action. It proposes
a random, syntactically valid custom ID; the user must still confirm the change.
Old ID bookmarks cease to work after a successful change.
