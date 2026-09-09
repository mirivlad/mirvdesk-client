Name:       mirvdesk
Version:    1.5.0
Release:    0
Summary:    RPM package
License:    GPL-3.0
URL:        https://github.com/mirivlad/mirvdesk-client
Vendor:     MirvDesk Project
Requires:   gtk3 libxcb1 libXfixes3 alsa-utils libXtst6 libva2 gstreamer-plugins-base gstreamer-plugin-pipewire
Recommends: libayatana-appindicator3-1 xdotool
Provides:   libdesktop_drop_plugin.so()(64bit), libdesktop_multi_window_plugin.so()(64bit), libfile_selector_linux_plugin.so()(64bit), libflutter_custom_cursor_plugin.so()(64bit), libflutter_linux_gtk.so()(64bit), libscreen_retriever_plugin.so()(64bit), libtray_manager_plugin.so()(64bit), liburl_launcher_linux_plugin.so()(64bit), libwindow_manager_plugin.so()(64bit), libwindow_size_plugin.so()(64bit), libtexture_rgba_renderer_plugin.so()(64bit)

# https://docs.fedoraproject.org/en-US/packaging-guidelines/Scriptlets/

%description
MirvDesk is a self-hosted remote desktop client based on RustDesk.

%prep
# we have no source, so nothing here

%build
# we have no source, so nothing here

# %global __python %{__python3}

%install

mkdir -p "%{buildroot}/usr/share/mirvdesk" && cp -r ${HBB}/flutter/build/linux/x64/release/bundle/* -t "%{buildroot}/usr/share/mirvdesk"
mkdir -p "%{buildroot}/usr/bin"
install -Dm 644 $HBB/res/rustdesk.service "%{buildroot}/usr/share/mirvdesk/files/mirvdesk.service"
install -Dm 644 $HBB/res/rustdesk.desktop "%{buildroot}/usr/share/mirvdesk/files/mirvdesk.desktop"
install -Dm 644 $HBB/res/rustdesk-link.desktop "%{buildroot}/usr/share/mirvdesk/files/mirvdesk-link.desktop"
install -Dm 644 $HBB/res/128x128@2x.png "%{buildroot}/usr/share/icons/hicolor/256x256/apps/mirvdesk.png"
install -Dm 644 $HBB/res/scalable.svg "%{buildroot}/usr/share/icons/hicolor/scalable/apps/mirvdesk.svg"

%files
/usr/share/mirvdesk/*
/usr/share/mirvdesk/files/mirvdesk.service
/usr/share/icons/hicolor/256x256/apps/mirvdesk.png
/usr/share/icons/hicolor/scalable/apps/mirvdesk.svg
/usr/share/mirvdesk/files/mirvdesk.desktop
/usr/share/mirvdesk/files/mirvdesk-link.desktop

%changelog
# let's skip this for now

%pre
# can do something for centos7
case "$1" in
  1)
    # for install
  ;;
  2)
    # for upgrade
    systemctl stop mirvdesk || true
  ;;
esac

%post
cp /usr/share/mirvdesk/files/mirvdesk.service /etc/systemd/system/mirvdesk.service
cp /usr/share/mirvdesk/files/mirvdesk.desktop /usr/share/applications/
cp /usr/share/mirvdesk/files/mirvdesk-link.desktop /usr/share/applications/
ln -sf /usr/share/mirvdesk/mirvdesk /usr/bin/mirvdesk
systemctl daemon-reload
systemctl enable mirvdesk
systemctl start mirvdesk
update-desktop-database

%preun
case "$1" in
  0)
    # for uninstall
    systemctl stop mirvdesk || true
    systemctl disable mirvdesk || true
    rm /etc/systemd/system/mirvdesk.service || true
  ;;
  1)
    # for upgrade
  ;;
esac

%postun
case "$1" in
  0)
    # for uninstall
    rm /usr/bin/mirvdesk || true
    rmdir /usr/lib/mirvdesk || true
    rmdir /usr/local/mirvdesk || true
    rmdir /usr/share/mirvdesk || true
    rm /usr/share/applications/mirvdesk.desktop || true
    rm /usr/share/applications/mirvdesk-link.desktop || true
    update-desktop-database
  ;;
  1)
    # for upgrade
    rmdir /usr/lib/mirvdesk || true
    rmdir /usr/local/mirvdesk || true
  ;;
esac
