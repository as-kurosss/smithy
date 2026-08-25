//! Python-сервер: запуск при старте приложения и проверка здоровья.

use std::process::{Child, Command};
use std::sync::Mutex;
use std::time::Duration;

use reqwest::blocking::Client;
use serde_json::Value;

/// Базовый URL Python-сервера.
const BASE_URL: &str = "http://127.0.0.1:9500";

/// Общее состояние приложения: HTTP-клиент для проксирования в Python-сервер.
pub struct AppState {
    pub client: Client,
}

impl AppState {
    /// Создаёт новое состояние.
    pub fn new() -> Self {
        Self {
            client: Client::builder()
                .timeout(Duration::from_secs(30))
                .build()
                .expect("Failed to create HTTP client"),
        }
    }

    /// Выполняет GET-запрос и возвращает JSON.
    pub fn proxy_get(&self, path: &str) -> Result<Value, String> {
        let url = format!("{BASE_URL}{path}");
        let resp = self
            .client
            .get(&url)
            .send()
            .map_err(|e| format!("HTTP error: {e}"))?;

        if resp.status().is_success() {
            resp.json::<Value>()
                .map_err(|e| format!("JSON parse error: {e}"))
        } else {
            let status = resp.status();
            let body = resp.text().unwrap_or_default();
            Err(format!("HTTP {status}: {body}"))
        }
    }

    /// Выполняет POST-запрос с JSON-телой и возвращает JSON.
    pub fn proxy_post(&self, path: &str, body: &Value) -> Result<Value, String> {
        let url = format!("{BASE_URL}{path}");
        let resp = self
            .client
            .post(&url)
            .json(body)
            .send()
            .map_err(|e| format!("HTTP error: {e}"))?;

        if resp.status().is_success() {
            resp.json::<Value>()
                .map_err(|e| format!("JSON parse error: {e}"))
        } else {
            let status = resp.status();
            let body = resp.text().unwrap_or_default();
            Err(format!("HTTP {status}: {body}"))
        }
    }
}

/// Состояние дочернего процесса Python-сервера.
pub struct PythonServer {
    child: Mutex<Option<Child>>,
}

impl PythonServer {
    /// Создаёт новый экземпляр.
    pub fn new() -> Self {
        Self {
            child: Mutex::new(None),
        }
    }

    /// Запускает Python-сервер и ждёт, пока он будет готов.
    ///
    /// Если сервер уже запущен на порту — переиспользует его.
    ///
    /// # Errors
    ///
    /// Возвращает ошибку, если не удалось запустить процесс или сервер не стал готов.
    pub fn start(&self) -> Result<(), String> {
        let probe = Client::builder()
            .timeout(Duration::from_secs(2))
            .build()
            .map_err(|e| format!("Failed to create HTTP client: {e}"))?;

        // Check if a server is already running on the port.
        if let Ok(resp) = probe.get(format!("{BASE_URL}/health")).send() {
            if resp.status().is_success() {
                eprintln!("Python server already running on {BASE_URL}");
                return Ok(());
            }
        }

        // Kill any stale process on the port.
        let _ = kill_process_on_port(9500);

        let python = find_python().ok_or("Python not found in PATH")?;
        let mut child = Command::new(python)
            .args(["-m", "smithy", "--port", "9500"])
            .spawn()
            .map_err(|e| format!("Failed to start Python server: {e}"))?;

        // Wait for server to be ready (up to 5 seconds).
        for _ in 0..25 {
            if let Ok(resp) = probe.get(format!("{BASE_URL}/health")).send() {
                if resp.status().is_success() {
                    *self.child.lock().map_err(|e| e.to_string())? = Some(child);
                    return Ok(());
                }
            }
            std::thread::sleep(Duration::from_millis(200));
        }

        // Kill the process if it didn't start in time.
        let _ = child.kill();
        Err("Python server failed to start within 5 seconds".into())
    }

    /// Останавливает Python-сервер.
    pub fn stop(&self) {
        if let Ok(mut guard) = self.child.lock() {
            if let Some(ref mut child) = *guard {
                let _ = child.kill();
            }
            *guard = None;
        }
    }
}

impl Drop for PythonServer {
    fn drop(&mut self) {
        self.stop();
    }
}

/// Попытка найти исполняемый файл Python.
fn find_python() -> Option<String> {
    for name in &["python", "python3"] {
        if Command::new(name)
            .arg("--version")
            .output()
            .is_ok()
        {
            return Some(name.to_string());
        }
    }
    None
}

/// Убить процесс, занимающий указанный порт (Windows).
fn kill_process_on_port(port: u16) -> Result<(), String> {
    // netstat -ano -p TCP | findstr :PORT
    let output = Command::new("netstat")
        .args(["-ano", "-p", "TCP"])
        .output()
        .map_err(|e| format!("netstat failed: {e}"))?;

    let stdout = String::from_utf8_lossy(&output.stdout);
    let needle = format!(":{port}");

    for line in stdout.lines() {
        if line.contains(&needle) && line.contains("LISTENING") {
            // Last column is PID.
            if let Some(pid_str) = line.split_whitespace().last() {
                if let Ok(pid) = pid_str.parse::<u32>() {
                    let _ = Command::new("taskkill")
                        .args(["/F", "/PID", &pid.to_string()])
                        .output();
                }
            }
        }
    }
    Ok(())
}
