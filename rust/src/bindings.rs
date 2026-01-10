// rust/src/bindings.rs
use pyo3::prelude::*;
use pyo3_asyncio::tokio::future_into_py;
use serde_json;
use std::sync::Arc;
use tokio::sync::Mutex;

use crate::orca_client::{OrcaClient, WhirlpoolData, SwapQuote};

// Estructura envuelta para compartir entre threads
#[pyclass]
struct PyOrcaClient {
    client: Arc<Mutex<OrcaClient>>,
}

#[pymethods]
impl PyOrcaClient {
    #[new]
    fn new(rpc_url: String) -> Self {
        PyOrcaClient {
            client: Arc::new(Mutex::new(OrcaClient::new(&rpc_url))),
        }
    }

    /// Obtener balance de una wallet (síncrono)
    fn get_balance_sync(&self, wallet_address: String) -> PyResult<u64> {
        Python::with_gil(|py| {
            py.allow_threads(|| {
                let client = self.client.blocking_lock();
                match client.get_balance(&wallet_address) {
                    Ok(balance) => Ok(balance),
                    Err(e) => Err(PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(
                        format!("Error getting balance: {}", e),
                    )),
                }
            })
        })
    }

    /// Obtener datos de un Whirlpool
    fn get_whirlpool_data(&self, whirlpool_address: String) -> PyResult<String> {
        Python::with_gil(|py| {
            py.allow_threads(|| {
                let client = self.client.blocking_lock();
                match client.get_whirlpool_data(&whirlpool_address) {
                    Ok(data) => serde_json::to_string(&data)
                        .map_err(|e| {
                            PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(
                                format!("JSON serialization error: {}", e),
                            )
                        }),
                    Err(e) => Err(PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(
                        format!("Error getting whirlpool data: {}", e),
                    )),
                }
            })
        })
    }

    /// Obtener cotización de swap
    fn get_swap_quote(
        &self,
        input_mint: String,
        output_mint: String,
        amount: u64,
        slippage_bps: u16,
    ) -> PyResult<String> {
        Python::with_gil(|py| {
            py.allow_threads(|| {
                let client = self.client.blocking_lock();
                match client.get_swap_quote(&input_mint, &output_mint, amount, slippage_bps) {
                    Ok(quote) => serde_json::to_string(&quote)
                        .map_err(|e| {
                            PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(
                                format!("JSON serialization error: {}", e),
                            )
                        }),
                    Err(e) => Err(PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(
                        format!("Error getting swap quote: {}", e),
                    )),
                }
            })
        })
    }

    /// Encontrar Whirlpools para un par de tokens
    fn find_whirlpools(&self, token_a: String, token_b: String) -> PyResult<String> {
        Python::with_gil(|py| {
            py.allow_threads(|| {
                let client = self.client.blocking_lock();
                match client.find_whirlpools(&token_a, &token_b) {
                    Ok(pools) => serde_json::to_string(&pools)
                        .map_err(|e| {
                            PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(
                                format!("JSON serialization error: {}", e),
                            )
                        }),
                    Err(e) => Err(PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(
                        format!("Error finding whirlpools: {}", e),
                    )),
                }
            })
        })
    }

    /// Método asíncrono para obtener balance
    fn get_balance_async<'py>(
        slf: PyRef<'py, Self>,
        py: Python<'py>,
        wallet_address: String,
    ) -> PyResult<&'py PyAny> {
        let client = slf.client.clone();
        
        future_into_py(py, async move {
            let client = client.lock().await;
            match client.get_balance(&wallet_address) {
                Ok(balance) => Ok(balance),
                Err(e) => Err(PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(
                    format!("Error getting balance: {}", e),
                )),
            }
        })
    }

    /// Obtener program ID de Whirlpool
    #[getter]
    fn whirlpool_program_id(&self) -> String {
        OrcaClient::whirlpool_program_id().to_string()
    }

    /// Verificar conexión RPC
    fn check_connection(&self) -> PyResult<bool> {
        Python::with_gil(|py| {
            py.allow_threads(|| {
                let client = self.client.blocking_lock();
                // Intentar obtener el slot actual como prueba de conexión
                match client.get_latest_slot() {
                    Ok(_) => Ok(true),
                    Err(_) => Ok(false),
                }
            })
        })
    }
}

// Implementar método adicional en OrcaClient
impl OrcaClient {
    fn get_latest_slot(&self) -> Result<u64, Box<dyn std::error::Error>> {
        // En una implementación real, usarías el cliente RPC
        // Por ahora simulamos una respuesta
        Ok(123456789)
    }
}

// Registrar el módulo
pub fn register_module(py: Python, m: &PyModule) -> PyResult<()> {
    m.add_class::<PyOrcaClient>()?;
    
    // Constantes útiles
    m.add("ORCA_WHIRLPOOL_PROGRAM_ID", "whirLbMiicVdio4qvUfM5KAg6Ct8VwpYzGff3uctyCc")?;
    m.add("SOL_MINT", "So11111111111111111111111111111111111111112")?;
    m.add("USDC_MINT", "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v")?;
    m.add("USDT_MINT", "Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB")?;
    m.add("ORCA_MINT", "orcaEKTdK7LKz57vaAYr9QeNsVEPfiu6QeMU1kektZE")?;
    
    // Tipos de fee comunes en Orca
    m.add("FEE_TIER_STANDARD", 300)?;      // 0.3%
    m.add("FEE_TIER_LOW", 100)?;           // 0.1%
    m.add("FEE_TIER_HIGH", 1000)?;         // 1.0%
    
    Ok(())
}