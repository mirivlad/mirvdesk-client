#[cfg(windows)]
fn build_windows() {
    let file = "src/platform/windows.cc";
    let file2 = "src/platform/windows_delete_test_cert.cc";
    cc::Build::new().file(file).file(file2).compile("windows");
    println!("cargo:rustc-link-lib=WtsApi32");
    println!("cargo:rerun-if-changed={}", file);
    println!("cargo:rerun-if-changed={}", file2);
}

#[cfg(target_os = "macos")]
fn build_mac() {
    let file = "src/platform/macos.mm";
    let mut b = cc::Build::new();
    if let Ok(os_version::OsVersion::MacOS(v)) = os_version::detect() {
        let v = v.version;
        if v.contains("10.14") {
            b.flag("-DNO_InputMonitoringAuthStatus=1");
        }
    }
    b.flag("-std=c++17").file(file).compile("macos");
    println!("cargo:rerun-if-changed={}", file);
}

#[cfg(all(windows, feature = "inline"))]
fn build_manifest() {
    use std::io::Write;
    if std::env::var("PROFILE").unwrap() == "release" {
        let mut res = winres::WindowsResource::new();
        res.set_icon("res/icon.ico")
            .set_language(winapi::um::winnt::MAKELANGID(
                winapi::um::winnt::LANG_ENGLISH,
                winapi::um::winnt::SUBLANG_ENGLISH_US,
            ))
            .set_manifest_file("res/manifest.xml");
        match res.compile() {
            Err(e) => {
                write!(std::io::stderr(), "{}", e).unwrap();
                std::process::exit(1);
            }
            Ok(_) => {}
        }
    }
}

// bionic only exports getifaddrs()/freeifaddrs() from API 24, while the jniLibs
// are built against the API 21 sysroot (flutter/ndk_*.sh). webrtc-util calls
// them, so without this the android link fails on undefined symbols.
fn build_android_ifaddrs() {
    let file = "src/platform/android_ifaddrs.c";
    cc::Build::new().file(file).compile("android_ifaddrs");
    println!("cargo:rerun-if-changed={}", file);
}

fn install_android_deps() {
    let target_os = std::env::var("CARGO_CFG_TARGET_OS").unwrap();
    if target_os != "android" {
        return;
    }
    let mut target_arch = std::env::var("CARGO_CFG_TARGET_ARCH").unwrap();
    if target_arch == "x86_64" {
        target_arch = "x64".to_owned();
    } else if target_arch == "x86" {
        target_arch = "x86".to_owned();
    } else if target_arch == "aarch64" {
        target_arch = "arm64".to_owned();
    } else {
        target_arch = "arm".to_owned();
    }
    let target = format!("{}-android", target_arch);
    let vcpkg_root = std::env::var("VCPKG_ROOT").unwrap();
    let mut path: std::path::PathBuf = vcpkg_root.into();
    if let Ok(vcpkg_root) = std::env::var("VCPKG_INSTALLED_ROOT") {
        path = vcpkg_root.into();
    } else {
        path.push("installed");
    }
    path.push(target);
    println!(
        "cargo:rustc-link-search={}",
        path.join("lib").to_str().unwrap()
    );
    println!("cargo:rustc-link-lib=ndk_compat");
    println!("cargo:rustc-link-lib=c++");
    println!("cargo:rustc-link-lib=OpenSLES");
}

fn configure_mirvdesk_default_server() {
    const LOCAL_PATH: &str = "mirvdesk.local.conf";
    let from_env = std::env::var("MIRVDESK_SERVER_URL").unwrap_or_default();
    let local = std::fs::read_to_string(LOCAL_PATH).unwrap_or_default();
    let from_file = local
        .lines()
        .map(str::trim)
        .filter(|line| !line.is_empty() && !line.starts_with('#'))
        .find_map(|line| line.strip_prefix("server_url="))
        .map(str::trim)
        .unwrap_or("");
    let url = if from_env.trim().is_empty() {
        from_file
    } else {
        from_env.trim()
    };
    println!("cargo:rustc-env=MIRVDESK_DEFAULT_SERVER_URL={}", url);
    println!("cargo:rerun-if-env-changed=MIRVDESK_SERVER_URL");
    println!("cargo:rerun-if-changed={}", LOCAL_PATH);
}

fn main() {
    hbb_common::gen_version();
    configure_mirvdesk_default_server();
    install_android_deps();
    #[cfg(all(windows, feature = "inline"))]
    build_manifest();
    #[cfg(windows)]
    build_windows();
    let target_os = std::env::var("CARGO_CFG_TARGET_OS").unwrap();
    if target_os == "macos" {
        #[cfg(target_os = "macos")]
        build_mac();
        println!("cargo:rustc-link-lib=framework=ApplicationServices");
    }
    if target_os == "android" {
        build_android_ifaddrs();
    }
    println!("cargo:rerun-if-changed=build.rs");
}
