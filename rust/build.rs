// rust/build.rs
fn main() {
    // Configurar para Python 3.10
    pyo3_build_config::add_extension_module_link_args();
    
    // Para Windows, necesitamos configurar específicamente
    if cfg!(target_os = "windows") {
        println!("cargo:rustc-link-arg=/EXPORT:PyInit_orca_rust_bridge");
    }
}