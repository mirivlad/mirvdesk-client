//! MirvDesk release discovery, deliberately isolated from api.rustdesk.com.
use hbb_common::{bail, ResultType};
use reqwest::blocking::Client;
use serde_json::Value;
use std::time::Duration;

const API: &str = "https://api.github.com/repos/mirivlad/mirvdesk-client/releases?per_page=30";
const REPO: &str = "mirivlad/mirvdesk-client";
const MAX_DOWNLOAD: u64 = 300 * 1024 * 1024;

#[derive(Clone, Debug)]
pub struct GithubReleaseAsset {
    pub tag: String,
    pub url: String,
    pub digest: String,
    pub size: u64,
}

fn version_key(value: &str) -> Option<(u32, u32, u32, u32)> {
    let version = value.strip_prefix('v').unwrap_or(value);
    let (version, pre) = match version.split_once('-') {
        Some((base, suffix)) => (base, Some(suffix.parse::<u32>().ok()?)),
        None => (version, None),
    };
    let mut parts = version.split('.');
    let a = parts.next()?.parse().ok()?;
    let b = parts.next()?.parse().ok()?;
    let c = parts.next()?.parse().ok()?;
    if parts.next().is_some() {
        return None;
    }
    Some((a, b, c, pre.unwrap_or(1_000_000)))
}

fn release_asset_name(tag: &str) -> Option<String> {
    let ver = tag.strip_prefix('v').unwrap_or(tag);
    if version_key(tag).is_none() {
        return None;
    }
    #[cfg(target_os = "windows")]
    {
        let arch = crate::platform::windows::release_arch_suffix()?;
        let ext = if crate::platform::is_msi_installed().unwrap_or(false) {
            "msi"
        } else {
            "exe"
        };
        return Some(format!("mirvdesk-{ver}-{arch}.{ext}"));
    }
    #[cfg(target_os = "linux")]
    {
        let arch = match std::env::consts::ARCH {
            "x86_64" => "x86_64",
            "aarch64" => "aarch64",
            _ => return None,
        };
        return Some(format!("mirvdesk-{ver}-{arch}.deb"));
    }
    #[cfg(target_os = "macos")]
    {
        let arch = match std::env::consts::ARCH {
            "x86_64" => "x86_64",
            "aarch64" => "aarch64",
            _ => return None,
        };
        return Some(format!("mirvdesk-{ver}-{arch}-{arch}.dmg"));
    }
    #[cfg(any(target_os = "android", target_os = "ios"))]
    {
        return None;
    }
}

/// Only versioned assets published under *this fork*. Stable builds never
/// update to a preview; installing a preview opts into preview updates.
fn select_asset(
    releases: &Value,
    current: &str,
    expected_asset: impl Fn(&str) -> Option<String>,
) -> Option<GithubReleaseAsset> {
    let current = version_key(current)?;
    let preview_channel = current.3 != 1_000_000;
    let mut candidates: Vec<&Value> = releases.as_array()?.iter().collect();
    candidates
        .sort_by_key(|r| version_key(r["tag_name"].as_str().unwrap_or("")).unwrap_or((0, 0, 0, 0)));
    for release in candidates.into_iter().rev() {
        let tag = release["tag_name"].as_str()?;
        let Some(key) = version_key(tag) else {
            continue;
        };
        if release["draft"].as_bool() == Some(true) || key <= current {
            continue;
        }
        if !preview_channel && release["prerelease"].as_bool() == Some(true) {
            continue;
        }
        let Some(filename) = expected_asset(tag) else {
            continue;
        };
        let url_expected = format!("https://github.com/{REPO}/releases/download/{tag}/{filename}");
        let Some(assets) = release["assets"].as_array() else {
            continue;
        };
        for asset in assets {
            if asset["name"].as_str() != Some(filename.as_str())
                || asset["browser_download_url"].as_str() != Some(url_expected.as_str())
            {
                continue;
            }
            let Some(digest) = asset["digest"]
                .as_str()
                .and_then(|s| s.strip_prefix("sha256:"))
            else {
                continue;
            };
            if digest.len() != 64 || !digest.bytes().all(|b| b.is_ascii_hexdigit()) {
                continue;
            }
            let Some(size) = asset["size"].as_u64() else {
                continue;
            };
            if size == 0 || size > MAX_DOWNLOAD {
                continue;
            }
            return Some(GithubReleaseAsset {
                tag: tag.into(),
                url: url_expected,
                digest: digest.into(),
                size,
            });
        }
    }
    None
}

pub fn github_release_update() -> ResultType<Option<GithubReleaseAsset>> {
    let client = Client::builder()
        .timeout(Duration::from_secs(35))
        .redirect(reqwest::redirect::Policy::none())
        .build()?;
    let response = client
        .get(API)
        .header(
            reqwest::header::USER_AGENT,
            "MirvDesk-selfhosted-update/1.7",
        )
        .send()?
        .error_for_status()?;
    let releases: Value = response.json()?;
    Ok(select_asset(&releases, crate::VERSION, release_asset_name))
}

#[cfg(target_os = "windows")]
pub fn update_windows_from_github() -> ResultType<()> {
    use hbb_common::sha2::{Digest, Sha256};
    use std::{
        fs,
        io::{Read, Write},
    };
    if !super::has_no_active_conns() {
        return Ok(());
    }
    let Some(asset) = github_release_update()? else {
        return Ok(());
    };
    let client = Client::builder()
        .timeout(Duration::from_secs(180))
        .build()?;
    // Random and per-process directory: never execute a guessed filename from
    // the shared temp directory.
    let directory = std::env::temp_dir().join(format!(
        "mirvdesk-upgrade-{}-{:016x}",
        std::process::id(),
        hbb_common::rand::random::<u64>()
    ));
    fs::create_dir(&directory)?;
    let filename = asset.url.rsplit('/').next().unwrap_or_default();
    let path = directory.join(filename);
    let result = (|| -> ResultType<()> {
        let mut stream = client.get(&asset.url).send()?.error_for_status()?;
        let mut output = fs::OpenOptions::new()
            .write(true)
            .create_new(true)
            .open(&path)?;
        let mut hasher = Sha256::new();
        let mut total = 0u64;
        let mut buffer = [0u8; 65536];
        loop {
            let n = stream.read(&mut buffer)?;
            if n == 0 {
                break;
            }
            total += n as u64;
            if total > asset.size || total > MAX_DOWNLOAD {
                bail!("Unexpected update size");
            }
            hasher.update(&buffer[..n]);
            output.write_all(&buffer[..n])?;
        }
        output.sync_all()?;
        let calculated: String = hasher
            .finalize()
            .iter()
            .map(|b| format!("{b:02x}"))
            .collect();
        if total != asset.size || calculated != asset.digest {
            bail!("MirvDesk release asset failed SHA-256 verification");
        }
        if !super::has_no_active_conns() {
            bail!("Remote session became active; update deferred");
        }
        let is_msi = filename.ends_with(".msi");
        super::update_new_version(is_msi, &asset.tag, &path);
        Ok(())
    })();
    if result.is_err() {
        fs::remove_file(&path).ok();
        fs::remove_dir(&directory).ok();
    }
    result
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn parses_preview_version_ordering() {
        assert!(version_key("v1.7.0-2") > version_key("1.7.0-1"));
        assert!(version_key("v1.7.0") > version_key("v1.7.0-999"));
        assert!(version_key("v1.8.0-1") > version_key("v1.7.0"));
        assert!(version_key("garbage").is_none());
    }
    #[test]
    fn only_this_repository_and_verified_asset_can_be_selected() {
        let payload = serde_json::json!([{
            "tag_name":"v1.7.0-2", "prerelease":true, "draft":false,
            "assets":[{
                "name":"mirvdesk-1.7.0-2-x86_64.deb",
                "browser_download_url":"https://github.com/mirivlad/mirvdesk-client/releases/download/v1.7.0-2/mirvdesk-1.7.0-2-x86_64.deb",
                "digest":format!("sha256:{}", "a".repeat(64)),
                "size":12345
            }]
        }]);
        let name = |tag: &str| {
            Some(format!(
                "mirvdesk-{}-x86_64.deb",
                tag.trim_start_matches('v')
            ))
        };
        assert!(select_asset(&payload, "1.7.0-1", name).is_some());
        assert!(select_asset(&payload, "1.6.2", name).is_none());
        let mut tampered = payload.clone();
        tampered[0]["assets"][0]["browser_download_url"] =
            serde_json::json!("https://github.com/rustdesk/rustdesk/");
        assert!(select_asset(&tampered, "1.7.0-1", name).is_none());
    }
}
