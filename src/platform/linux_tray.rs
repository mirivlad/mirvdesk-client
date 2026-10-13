use gtk::{gio, glib, prelude::*};
use hbb_common::log;
use std::{cell::RefCell, rc::Rc, time::Duration};
use tray_icon::{menu::Menu, TrayIcon};

pub struct TrayRegistrationGuard {
    watcher: gio::DBusProxy,
    handler: Option<glib::SignalHandlerId>,
    pending: Rc<RefCell<Option<glib::SourceId>>>,
}

impl Drop for TrayRegistrationGuard {
    fn drop(&mut self) {
        if let Some(handler) = self.handler.take() {
            self.watcher.disconnect(handler);
        }
        if let Some(source) = self.pending.borrow_mut().take() {
            source.remove();
        }
    }
}

pub fn watch_tray_registration(tray: &TrayIcon, menu: &Menu) -> Option<TrayRegistrationGuard> {
    let watcher = match gio::DBusProxy::for_bus_sync(
        gio::BusType::Session,
        gio::DBusProxyFlags::DO_NOT_AUTO_START
            | gio::DBusProxyFlags::DO_NOT_LOAD_PROPERTIES
            | gio::DBusProxyFlags::DO_NOT_CONNECT_SIGNALS,
        None,
        "org.kde.StatusNotifierWatcher",
        "/StatusNotifierWatcher",
        "org.kde.StatusNotifierWatcher",
        None::<&gio::Cancellable>,
    ) {
        Ok(watcher) => watcher,
        Err(err) => {
            log::warn!("Failed to watch tray registration: {err}");
            return None;
        }
    };
    let pending = Rc::new(RefCell::new(None::<glib::SourceId>));
    let refresh_pending = pending.clone();
    let tray = tray.clone();
    let menu = menu.clone();
    let refresh = move |watcher: &gio::DBusProxy| {
        if let Some(source) = refresh_pending.borrow_mut().take() {
            source.remove();
        }
        if watcher.name_owner().is_none() {
            return;
        }
        let pending = refresh_pending.clone();
        let tray = tray.clone();
        let menu = menu.clone();
        // libayatana-appindicator can leave its 100 ms fallback timer armed
        // after registration succeeds. Reapplying the menu registers again
        // after that timer, letting the library remove its legacy icon.
        let source = glib::timeout_add_local_once(Duration::from_millis(200), move || {
            pending.borrow_mut().take();
            tray.set_menu(Some(Box::new(menu)));
        });
        *refresh_pending.borrow_mut() = Some(source);
    };
    refresh(&watcher);
    let handler = watcher.connect_notify_local(Some("g-name-owner"), move |watcher, _| {
        refresh(watcher);
    });
    Some(TrayRegistrationGuard {
        watcher,
        handler: Some(handler),
        pending,
    })
}
