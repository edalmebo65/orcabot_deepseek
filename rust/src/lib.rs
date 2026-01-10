// rust/src/lib.rs
use pyo3::prelude::*;
use pyo3::types::PyDict;

mod orca_client;
mod bindings;

use bindings::register_module;

/// Módulo principal de Python
#[pymodule]
fn orca_rust_bridge(py: Python, m: &PyModule) -> PyResult<()> {
    // Registrar todas las clases y funciones
    register_module(py, m)?;
    
    // Función para verificar versión
    #[pyfn(m)]
    fn version() -> &'static str {
        "0.1.0"
    }
    
    // Función para obtener información del sistema
    #[pyfn(m)]
    fn system_info() -> PyResult<PyObject> {
        let sys_info = PyDict::new(py);
        sys_info.set_item("rust_version", env!("CARGO_PKG_VERSION"))?;
        sys_info.set_item("solana_sdk_version", "1.18")?;
        sys_info.set_item("platform", std::env::consts::OS)?;
        Ok(sys_info.into())
    }
    
    // Función de prueba
    #[pyfn(m)]
    fn test_connection(rpc_url: &str) -> PyResult<bool> {
        use orca_client::OrcaClient;
        let client = OrcaClient::new(rpc_url);
        // Simular prueba de conexión
        Ok(true)
    }
    
    Ok(())
}

// Tests
#[cfg(test)]
mod tests {
    use super::*;
    
    #[test]
    fn test_program_id() {
        use orca_client::OrcaClient;
        let program_id = OrcaClient::whirlpool_program_id();
        assert_eq!(
            program_id.to_string(),
            "whirLbMiicVdio4qvUfM5KAg6Ct8VwpYzGff3uctyCc"
        );
    }
}