Name:       mirvdesk
Version:    1.6.0
Release:    0
Summary:    RPM package
License:    GPL-3.0
URL:        https://github.com/mirivlad/mirvdesk-client
Vendor:     MirvDesk Project
Requires:   gtk3 libxcb1 libXfixes3 alsa-utils libXtst6 libva2 gstreamer-plugins-base gstreamer-plugin-pipewire
Recommends: libayatana-appindicator3-1 xdotool

# https://docs.fedoraproject.org/en-US/packaging-guidelines/Scriptlets/

%description
MirvDesk is a self-hosted remote desktop client based on RustDesk.

%prep
# we have no source, so nothing here

%build
# we have no source, so nothing here

%global __python %{__python3}

%install
mkdir -p %{buildroot}/usr/bin/
mkdir -p %{buildroot}/usr/share/mirvdesk/
mkdir -p %{buildroot}/usr/share/mirvdesk/files/
mkdir -p %{buildroot}/usr/share/icons/hicolor/256x256/apps/
mkdir -p %{buildroot}/usr/share/icons/hicolor/scalable/apps/
install -m 755 $HBB/target/release/rustdesk %{buildroot}/usr/bin/mirvdesk
install $HBB/libsciter-gtk.so %{buildroot}/usr/share/mirvdesk/libsciter-gtk.so
install -m 644 $HBB/res/rustdesk.service %{buildroot}/usr/share/mirvdesk/files/mirvdesk.service
install $HBB/res/128x128@2x.png %{buildroot}/usr/share/icons/hicolor/256x256/apps/mirvdesk.png
install $HBB/res/scalable.svg %{buildroot}/usr/share/icons/hicolor/scalable/apps/mirvdesk.svg
install -m 644 $HBB/res/rustdesk.desktop %{buildroot}/usr/share/mirvdesk/files/mirvdesk.desktop
install -m 644 $HBB/res/rustdesk-link.desktop %{buildroot}/usr/share/mirvdesk/files/mirvdesk-link.desktop

%files
/usr/bin/mirvdesk
/usr/share/mirvdesk/libsciter-gtk.so
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
    rm /usr/share/applications/mirvdesk.desktop || true
    rm /usr/share/applications/mirvdesk-link.desktop || true
    update-desktop-database
  ;;
  1)
    # for upgrade
  ;;
esac
