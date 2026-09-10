# RustDesk upstream compatibility policy

MirvDesk is intentionally maintained as a downstream of RustDesk. The project should remain easy to compare with, merge from and reason about against upstream for as long as practical.

This does **not** mean MirvDesk must behave identically to RustDesk. It means MirvDesk-specific behavior should be additive, isolated and negotiated wherever possible.

## Compatibility layers

### 1. Transport and remote-control engine

Treat the RustDesk transport, rendezvous/relay protocol, session engine, codecs, input, clipboard and file-transfer internals as upstream-owned code by default.

Change these areas only when a MirvDesk requirement cannot reasonably be implemented outside them. Keep such patches small and documented.

### 2. External application identity

MirvDesk must remain externally isolated from RustDesk so both applications can coexist: configuration paths, services, package IDs, URI scheme, branding and update identity are MirvDesk-specific.

Internal upstream names may remain when they are ABI/build implementation details and do not cause runtime state collisions. Cosmetic renaming is not worth permanent merge conflicts.

### 3. MirvDesk server extensions
When MirvDesk intentionally implements an upstream-facing feature, preserve the upstream route/shape expected by the client where practical. `Accessible devices / Groups` is an example.

MirvDesk-only administration and management APIs should use a clearly MirvDesk-owned namespace (for example `/api/mirvdesk/v1/...`) rather than occupying generic paths that upstream may later introduce.

Optional features must be capability-gated through `/.well-known/mirvdesk` and/or authenticated capability discovery. An older server should continue to provide the features it supports without a client-wide failure.

### 4. Client UI

Prefer a small conditional entry point into MirvDesk-specific screens over modifying upstream screens deeply. The planned administration console should live in its own Flutter modules and call the MirvDesk admin API through a narrow service/model layer.

Use existing upstream widgets/models where that does not couple MirvDesk business logic to upstream UI internals.

Theme changes should remain centralized in MirvDesk theme constants rather than spread as hard-coded colors across upstream files.

### 5. Data model

The MirvDesk Server database may evolve independently. Database compatibility with RustDesk Server Pro is not a goal.

However, internal schema details must not leak into client-facing API contracts. This allows migrations such as single-group to many-to-many device membership without forcing invasive client changes.

## Merge discipline
Before a MirvDesk-specific change touches an upstream-heavy area, ask:

1. Can this be implemented as a new module, adapter, capability or server endpoint instead?
2. Can an upstream data type or response shape be extended rather than replaced?
3. Will this create recurring conflicts on future upstream merges?
4. Does the change affect transport/protocol behavior or only MirvDesk management UX?
5. Can unsupported behavior fail closed or disappear cleanly on older servers?

Prefer upstream commits to be merged/rebased periodically in bounded batches rather than after a long period of divergence. Resolve branding and identity conflicts through the centralized MirvDesk hooks first.

Any intentional large divergence should be recorded in documentation with:

- the upstream area being changed;
- why an additive approach was insufficient;
- compatibility impact;
- expected future merge cost;
- tests that protect the MirvDesk behavior.

## Non-goal

Source files do not need to stop looking like RustDesk. The goal is a distinct, self-hosted MirvDesk product that can continue benefiting from upstream RustDesk engineering without sharing user state or silently depending on RustDesk infrastructure.