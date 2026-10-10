//! Signed MirvDesk inventory heartbeat. Deliberately independent of account
//! login; only the host service (not every GUI session) sends it.

use hbb_common::{config::Config, sodiumoxide::crypto::sign};
use serde_json::{json, Value};
use std::time::Duration;

fn heartbeat_message(
    id: &str,
    nonce: &str,
    hostname: &str,
    os: &str,
    arch: &str,
    version: &str,
) -> Vec<u8> {
    format!("mirvdesk-heartbeat-v1\n{id}\n{nonce}\n{hostname}\n{os}\n{arch}\n{version}")
        .into_bytes()
}

pub async fn send_heartbeat() -> Result<(), String> {
    // Don't attempt to register arbitrary RustDesk/custom rendezvous servers.
    if Config::get_option("mirvdesk-bootstrap-url").is_empty()
        || Config::get_option("stop-service") == "Y"
    {
        return Ok(());
    }
    let url = crate::ui_interface::get_api_server();
    let parsed = reqwest::Url::parse(&url).map_err(|e| e.to_string())?;
    if parsed.scheme() != "https"
        && !(parsed.scheme() == "http"
            && matches!(parsed.host_str(), Some("localhost" | "127.0.0.1" | "::1")))
    {
        return Ok(());
    }
    let id = Config::get_id();
    let (sk, _pk) = Config::get_key_pair();
    let secret = sign::SecretKey::from_slice(&sk).ok_or("no host signing key")?;
    if id.is_empty() {
        return Ok(());
    }
    let client = reqwest::Client::builder()
        .connect_timeout(Duration::from_secs(3))
        .timeout(Duration::from_secs(7))
        .build()
        .map_err(|e| e.to_string())?;
    let challenge: Value = client
        .get(format!("{url}/api/device-registry/challenge"))
        .query(&[("id", &id)])
        .send()
        .await
        .map_err(|e| e.to_string())?
        .error_for_status()
        .map_err(|e| e.to_string())?
        .json()
        .await
        .map_err(|e| e.to_string())?;
    let nonce = challenge
        .get("nonce")
        .and_then(Value::as_str)
        .ok_or("no nonce in registry challenge")?;
    let hostname = crate::common::hostname();
    let os = std::env::consts::OS;
    let arch = std::env::consts::ARCH;
    let version = env!("CARGO_PKG_VERSION");
    // All metadata is covered by the device's Ed25519 signature, not only
    // the nonce, so a proxy cannot substitute a hostname or OS.
    let signature = sign::sign_detached(
        &heartbeat_message(&id, nonce, &hostname, os, arch, version),
        &secret,
    );
    let body = json!({
        "id": id,
        "nonce": nonce,
        "hostname": hostname,
        "os": os,
        "arch": arch,
        "version": version,
        "signature": crate::encode64(signature.to_bytes()),
    });
    client
        .post(format!("{url}/api/device-registry/heartbeat"))
        .json(&body)
        .send()
        .await
        .map_err(|e| e.to_string())?
        .error_for_status()
        .map_err(|e| e.to_string())?;
    Ok(())
}

pub async fn heartbeat_loop() {
    tokio::time::sleep(Duration::from_secs(15)).await;
    loop {
        if let Err(e) = send_heartbeat().await {
            log::debug!("MirvDesk registry heartbeat: {e}");
        }
        tokio::time::sleep(Duration::from_secs(60)).await;
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn signature_payload_is_domain_separated() {
        let msg = heartbeat_message("123", "xyz", "PC", "windows", "x86_64", "1.7.3");
        assert_eq!(
            msg,
            b"mirvdesk-heartbeat-v1\n123\nxyz\nPC\nwindows\nx86_64\n1.7.3"
        );
    }
}
