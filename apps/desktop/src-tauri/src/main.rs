// FarmTwin desktop shell (ADR-022, ADR-027).
//
// Starts the bundled API on a free port, opens the window pointed at it, and on exit asks the
// API to shut down (it stops llama-server itself). The API also exits on its own if this
// process disappears, so a crash leaves nothing running.

#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use std::io::{BufRead, BufReader, Read, Write};
use std::net::TcpStream;
use std::path::Path;
use std::process::{Child, Command, Stdio};
use std::sync::mpsc;
use std::sync::Mutex;
use std::thread;
use std::time::{Duration, Instant};

use tauri::{AppHandle, Manager, RunEvent, WebviewUrl, WebviewWindowBuilder};

struct Api {
    child: Mutex<Option<Child>>,
    port: u16,
    token: String,
}

fn main() {
    let app = tauri::Builder::default()
        // a second launch focuses the open window instead of starting another API
        .plugin(tauri_plugin_single_instance::init(|app, _args, _cwd| {
            if let Some(window) = app.get_webview_window("main") {
                let _ = window.unminimize();
                let _ = window.set_focus();
            }
        }))
        .plugin(tauri_plugin_dialog::init())
        .plugin(tauri_plugin_updater::Builder::new().build())
        .plugin(tauri_plugin_process::init())
        .setup(|app| {
            let api = start_api(&app.path().resource_dir()?, &app.path().app_log_dir()?)?;
            let script = format!("window.__FARMTWIN_API__ = 'http://127.0.0.1:{}/api';", api.port);
            app.manage(api);
            WebviewWindowBuilder::new(app, "main", WebviewUrl::App("index.html".into()))
                .title("FarmTwin")
                .inner_size(1280.0, 820.0)
                .min_inner_size(900.0, 600.0)
                .initialization_script(&script)
                .build()?;
            Ok(())
        })
        .build(tauri::generate_context!())
        .expect("FarmTwin failed to start");

    app.run(|handle, event| {
        if let RunEvent::Exit = event {
            stop_api(handle);
        }
    });
}

/// Spawns the API with everything it needs to find, and waits for the port it picked.
fn start_api(resources: &Path, log_dir: &Path) -> Result<Api, Box<dyn std::error::Error>> {
    let exe = |name: &str| if cfg!(windows) { format!("{name}.exe") } else { name.to_string() };
    let token = uuid::Uuid::new_v4().simple().to_string();

    let mut cmd = Command::new(resources.join("api").join(exe("farmtwin-api")));
    cmd.env("FARMTWIN_PORT", "0")
        .env("FARMTWIN_PARENT_PID", std::process::id().to_string())
        .env("FARMTWIN_SHUTDOWN_TOKEN", &token)
        .env("FARMTWIN_LLAMA_SERVER_BIN", resources.join("llama").join(exe("llama-server")))
        .env("FARMTWIN_EMBEDDER_DIR", resources.join("embedder"))
        .stdout(Stdio::piped())
        .stderr(Stdio::from(std::fs::File::create(log_dir_file(log_dir, "api-console.log"))?));
    #[cfg(windows)]
    {
        use std::os::windows::process::CommandExt;
        cmd.creation_flags(0x0800_0000); // CREATE_NO_WINDOW: no console window behind the app
    }
    let mut child = cmd.spawn()?;

    // the first stdout line is FARMTWIN_PORT=<n>; keep draining after it so the pipe never fills
    let stdout = child.stdout.take().ok_or("no stdout from the API")?;
    let (tx, rx) = mpsc::channel();
    thread::spawn(move || {
        for line in BufReader::new(stdout).lines().map_while(Result::ok) {
            if let Some(port) = line.strip_prefix("FARMTWIN_PORT=") {
                let _ = tx.send(port.trim().parse::<u16>().unwrap_or(0));
            }
        }
    });
    let port = rx
        .recv_timeout(Duration::from_secs(120))
        .map_err(|_| "the FarmTwin background service didn't start")?;
    Ok(Api { child: Mutex::new(Some(child)), port, token })
}

fn log_dir_file(dir: &Path, name: &str) -> std::path::PathBuf {
    let _ = std::fs::create_dir_all(dir);
    dir.join(name)
}

/// Asks the API to stop (so it can stop llama-server), then makes sure it's gone.
fn stop_api(handle: &AppHandle) {
    let Some(api) = handle.try_state::<Api>() else { return };
    let Some(mut child) = api.child.lock().ok().and_then(|mut c| c.take()) else { return };

    let _ = post_shutdown(api.port, &api.token);
    let deadline = Instant::now() + Duration::from_secs(8);
    while Instant::now() < deadline {
        if let Ok(Some(_)) = child.try_wait() {
            return;
        }
        thread::sleep(Duration::from_millis(100));
    }
    let _ = child.kill();
}

/// A bare HTTP request: the shell only ever talks to its own API, so no HTTP client is needed.
fn post_shutdown(port: u16, token: &str) -> std::io::Result<()> {
    let mut stream = TcpStream::connect(("127.0.0.1", port))?;
    stream.set_read_timeout(Some(Duration::from_secs(2)))?;
    write!(
        stream,
        "POST /api/shutdown HTTP/1.1\r\nHost: 127.0.0.1\r\nX-FarmTwin-Token: {token}\r\nContent-Length: 0\r\nConnection: close\r\n\r\n"
    )?;
    let mut reply = [0u8; 64];
    let _ = stream.read(&mut reply);
    Ok(())
}
