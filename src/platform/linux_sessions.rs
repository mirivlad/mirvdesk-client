//! Read-only logind discovery. This deliberately does not select/activate
//! sessions: changing seat0 would redirect OTHER connections to another user.
//! Only a per-session media/IPC backend can safely support parallel desktops.
use std::{
    collections::HashMap,
    process::Command,
    sync::{Mutex, OnceLock},
    time::{Duration, Instant},
};

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct GraphicalSession {
    pub id: String,
    pub username: String,
    pub kind: String,
    pub seat: String,
    pub state: String,
    pub active: bool,
}

fn session_ids(output: &str) -> Vec<String> {
    let mut ids = Vec::new();
    for line in output.lines().take(64) {
        let Some(id) = line.split_whitespace().next() else {
            continue;
        };
        if id.len() > 32
            || id.is_empty()
            || id.starts_with('-')
            || !id.bytes().all(|c| c.is_ascii_alphanumeric() || c == b'-')
        {
            continue;
        }
        if !ids.iter().any(|existing| existing == id) {
            ids.push(id.to_owned());
        }
    }
    ids
}

fn parse_graphical_session(id: &str, properties: &str) -> Option<GraphicalSession> {
    let entries: HashMap<_, _> = properties
        .lines()
        .filter_map(|line| {
            let (key, value) = line.split_once('=')?;
            Some((key.trim(), value.trim()))
        })
        .collect();
    let kind = entries.get("Type")?.to_ascii_lowercase();
    if kind != "x11" && kind != "wayland" {
        return None;
    }
    // Greeters, SSH and lingering user managers are not desktop targets.
    let class = *entries.get("Class")?;
    if class != "user" && class != "user-light" {
        return None;
    }
    let username = *entries.get("Name")?;
    if username.is_empty() {
        return None;
    }
    Some(GraphicalSession {
        id: id.to_owned(),
        username: username.to_owned(),
        kind,
        seat: entries.get("Seat").copied().unwrap_or("").to_owned(),
        state: entries.get("State").copied().unwrap_or("").to_owned(),
        active: entries.get("Active").copied().unwrap_or("") == "yes",
    })
}

/// Enumerate graphical logind sessions without creating or switching sessions.
/// Call via spawn_blocking when invoked from an async connection handler.
/// A short cache prevents launching many loginctl processes when several
/// remote connections arrive at once.
pub fn list_graphical_sessions() -> Vec<GraphicalSession> {
    static CACHE: OnceLock<Mutex<Option<(Instant, Vec<GraphicalSession>)>>> = OnceLock::new();
    let cache = CACHE.get_or_init(|| Mutex::new(None));
    if let Ok(mut guard) = cache.lock() {
        if let Some((updated, sessions)) = guard.as_ref() {
            if updated.elapsed() < Duration::from_secs(3) {
                return sessions.clone();
            }
        }
        let sessions = query_graphical_sessions();
        *guard = Some((Instant::now(), sessions.clone()));
        return sessions;
    }
    query_graphical_sessions()
}

fn query_graphical_sessions() -> Vec<GraphicalSession> {
    let Ok(output) = Command::new("loginctl")
        .args(["list-sessions", "--no-legend", "--no-pager"])
        .output()
    else {
        return Vec::new();
    };
    if !output.status.success() {
        return Vec::new();
    }
    let listing = String::from_utf8_lossy(&output.stdout);
    let mut result = Vec::new();
    for id in session_ids(&listing) {
        let Ok(output) = Command::new("loginctl")
            .args(["show-session", id.as_str(), "--no-pager"])
            .output()
        else {
            continue;
        };
        if output.status.success() {
            let props = String::from_utf8_lossy(&output.stdout);
            if let Some(info) = parse_graphical_session(&id, &props) {
                result.push(info);
            }
        }
    }
    result
}

/// A target account may have several graphical desktops. A remote connection
/// may attach only to the session *already served* by its user --server.
/// The stable logind session ID is retained for the lifetime of the connection
/// to detect seat switches even when the Unix username is unchanged.
#[derive(Clone, Debug, PartialEq, Eq)]
pub enum SessionRoute {
    Served(String),
    Other(Vec<String>),
    Missing,
}

pub fn resolve_user_session(
    sessions: &[GraphicalSession],
    requested: &str,
    serving_user: &str,
) -> SessionRoute {
    let matches: Vec<&GraphicalSession> = sessions
        .iter()
        .filter(|s| s.username == requested)
        .collect();
    if requested == serving_user {
        if let Some(current) = matches.iter().find(|s| s.seat == "seat0" && s.active) {
            return SessionRoute::Served(current.id.clone());
        }
        // A manually started X11 session may still appear as Type=tty.
        // The existing server already serves it, but logind cannot pin it.
        if matches.is_empty() {
            return SessionRoute::Served(String::new());
        }
    }
    if matches.is_empty() {
        SessionRoute::Missing
    } else {
        SessionRoute::Other(matches.iter().map(|s| s.id.clone()).collect())
    }
}

/// Does the pinned graphical session still own the active seat0? Re-check this
/// before streaming input/video: another login with the *same username* is
/// not the same session and must not inherit the old connection.
pub fn pinned_session_is_current(
    sessions: &[GraphicalSession],
    session_id: &str,
    username: &str,
) -> bool {
    sessions
        .iter()
        .any(|s| s.id == session_id && s.username == username && s.seat == "seat0" && s.active)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn binds_only_the_served_desktop_not_another_user() {
        let alice = parse_graphical_session(
            "3",
            "Name=alice\nType=x11\nClass=user\nSeat=seat0\nActive=yes\n",
        )
        .unwrap();
        let bob = parse_graphical_session(
            "6",
            "Name=bob\nType=wayland\nClass=user\nSeat=\nActive=no\n",
        )
        .unwrap();
        let sessions = vec![alice, bob];
        assert_eq!(
            resolve_user_session(&sessions, "alice", "alice"),
            SessionRoute::Served("3".to_owned())
        );
        assert_eq!(
            resolve_user_session(&sessions, "bob", "alice"),
            SessionRoute::Other(vec!["6".to_owned()])
        );
        assert_eq!(
            resolve_user_session(&sessions, "nobody", "alice"),
            SessionRoute::Missing
        );
    }

    #[test]
    fn session_binding_does_not_follow_account_to_new_login() {
        let old = parse_graphical_session(
            "3",
            "Name=alice\nType=x11\nClass=user\nSeat=seat0\nActive=yes\n",
        )
        .unwrap();
        let new = parse_graphical_session(
            "9",
            "Name=alice\nType=x11\nClass=user\nSeat=seat0\nActive=yes\n",
        )
        .unwrap();
        assert!(pinned_session_is_current(&[old.clone()], "3", "alice"));
        assert!(!pinned_session_is_current(&[new.clone()], "3", "alice"));
        assert!(!pinned_session_is_current(&[old], "3", "bob"));
        assert_eq!(
            resolve_user_session(&[new], "alice", "alice"),
            SessionRoute::Served("9".to_owned())
        );
    }

    #[test]
    fn multiple_sessions_of_one_user_choose_only_active_seat() {
        let inactive = parse_graphical_session(
            "5",
            "Name=alice\nType=x11\nClass=user\nSeat=seat0\nActive=no\n",
        )
        .unwrap();
        let active = parse_graphical_session(
            "6",
            "Name=alice\nType=wayland\nClass=user\nSeat=seat0\nActive=yes\n",
        )
        .unwrap();
        assert_eq!(
            resolve_user_session(&[inactive, active], "alice", "alice"),
            SessionRoute::Served("6".into())
        );
    }

    #[test]
    fn listing_deduplicates_and_rejects_bad_ids() {
        let ids = session_ids(" 2 1000 alice seat0\n2 1000 alice seat0\n3 1001 bob -\n");
        assert_eq!(ids, vec!["2", "3"]);
        assert!(session_ids(" --evil 1000 alice\n").is_empty());
    }

    #[test]
    fn recognizes_graphical_sessions_and_ignores_tty_greeters() {
        let properties =
            "Name=alice\nType=wayland\nClass=user\nSeat=seat0\nActive=yes\nState=active\n";
        let session = parse_graphical_session("3", properties).unwrap();
        assert_eq!(session.username, "alice");
        assert_eq!(session.kind, "wayland");
        assert!(session.active);
        assert_eq!(session.seat, "seat0");
        assert!(parse_graphical_session("1", &properties.replace("wayland", "tty")).is_none());
        assert!(
            parse_graphical_session("1", &properties.replace("Class=user", "Class=greeter"))
                .is_none()
        );
        assert!(parse_graphical_session("1", "Name=\nType=x11\nClass=user\n").is_none());
    }

    #[test]
    fn x11_inactive_session_is_visible_without_activation() {
        let p = "Name=bob\nType=x11\nClass=user\nActive=no\nState=online\n";
        let s = parse_graphical_session("10", p).unwrap();
        assert!(!s.active);
        assert_eq!(s.state, "online");
    }
}
