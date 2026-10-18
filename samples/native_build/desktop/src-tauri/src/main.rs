fn main() {
    tauri::Builder::default()
        .run(tauri::generate_context!())
        .expect("native sample failed to run");
}
