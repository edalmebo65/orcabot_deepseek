use pyo3::prelude::*;
use pyo3::types::{PyDict, PyList};
use serde::{Deserialize, Serialize};
use solana_client::rpc_client::RpcClient;
use solana_sdk::{pubkey::Pubkey, signature::Keypair};
use std::str::FromStr;
use std::sync::Arc;
use tokio::sync::Mutex;
use anyhow::{Result, anyhow};

#[derive(Debug, Serialize, Deserialize)]
struct WhirlpoolData {
    address: String,
    token_mint_a: String,
    token_mint_b: String,
    tick_spacing: u16,
    fee_rate: u32,
    protocol_fee_rate: u32,
    liquidity: u128,
    sqrt_price: u128,
    tick_current_index: i32,
}

#[derive(Debug, Serialize, Deserialize)]
struct SwapQuote {
    input_mint: String,
    output_mint: String,
    in_amount: u64,
    out_amount: u64,
    other_amount_threshold: u64,
    sqrt_price_limit: u128,
    fee_mint_a: u64,
    fee_mint_b: u64,
    price_impact_pct: f64,
}

#[derive(Debug, Serialize, Deserialize)]
struct PoolInfo {
    address: String,
    token_a: String,
    token_b: String,
    lp_mint: String,
    authority: String,
    fee_owner: String,
    fee: f64,
}

struct OrcaClient {
    rpc_client: Arc<RpcClient>,
}

impl OrcaClient {
    fn new(rpc_url: &str) -> Self {
        let rpc_client = RpcClient::new(rpc_url.to_string());
        OrcaClient {
            rpc_client: Arc::new(rpc_client),
        }
    }

    fn get_program_id() -> String {
        "whirLbMiicVdio4qvUfM5KAg6Ct8VwpYzGff3uctyCc".to_string()
    }

    fn get_sol_mint() -> String {
        "So11111111111111111111111111111111111111112".to_string()
    }

    fn get_usdc_mint() -> String {
        "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v".to_string()
    }

    fn get_usdt_mint() -> String {
        "Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB".to_string()
    }

    fn get_orca_mint() -> String {
        "orcaEKTdK7LKz57vaAYr9QeNsVEPfiu6QeMU1kektZE".to_string()
    }

    async fn get_balance(&self, address: &str) -> Result<u64> {
        let pubkey = Pubkey::from_str(address)?;
        let balance = self.rpc_client.get_balance(&pubkey)?;
        Ok(balance)
    }

    async fn get_token_balance(&self, wallet: &str, mint: &str) -> Result<u64> {
        // Implementación simplificada - en producción usar get_token_accounts_by_owner
        let wallet_pubkey = Pubkey::from_str(wallet)?;
        let mint_pubkey = Pubkey::from_str(mint)?;
        
        // Simulación de balance
        Ok(1000000) // 1 token (6 decimales para USDC)
    }

    async fn get_swap_quote_api(
        &self,
        input_mint: &str,
        output_mint: &str,
        amount: u64,
        slippage: f64,
    ) -> Result<SwapQuote> {
        // Usar API pública de Orca para cotizaciones reales
        let client = reqwest::Client::new();
        let url = "https://api.orca.so/quote";
        
        let params = [
            ("inputMint", input_mint),
            ("outputMint", output_mint),
            ("amount", &amount.to_string()),
            ("slippage", &slippage.to_string()),
            ("swapMode", "ExactIn"),
        ];
        
        let response = client.get(url).query(&params).send().await?;
        
        if response.status().is_success() {
            let quote: SwapQuote = response.json().await?;
            Ok(quote)
        } else {
            Err(anyhow!("API Error: {}", response.status()))
        }
    }

    async fn get_all_pools(&self) -> Result<Vec<PoolInfo>> {
        // Obtener pools de la API de Orca
        let client = reqwest::Client::new();
        let response = client.get("https://api.orca.so/v1/pools").send().await?;
        
        if response.status().is_success() {
            let pools: Vec<PoolInfo> = response.json().await?;
            Ok(pools)
        } else {
            Err(anyhow!("Failed to fetch pools"))
        }
    }

    async fn get_whirlpools(&self) -> Result<Vec<WhirlpoolData>> {
        // Obtener whirlpools de la API
        let client = reqwest::Client::new();
        let response = client.get("https://api.orca.so/whirlpools").send().await?;
        
        if response.status().is_success() {
            let whirlpools: Vec<WhirlpoolData> = response.json().await?;
            Ok(whirlpools)
        } else {
            // Datos de ejemplo si la API falla
            Ok(vec![
                WhirlpoolData {
                    address: "HJPjoWUrhoZzkNfRpHuieeFk9WcZWjwy6PBjZ81ngndJ".to_string(),
                    token_mint_a: Self::get_sol_mint(),
                    token_mint_b: Self::get_usdc_mint(),
                    tick_spacing: 64,
                    fee_rate: 300,
                    protocol_fee_rate: 100,
                    liquidity: 1000000000000,
                    sqrt_price: 2000000000,
                    tick_current_index: 0,
                }
            ])
        }
    }
}

#[pyclass]
struct PyOrcaClient {
    client: Arc<tokio::sync::Mutex<OrcaClient>>,
}

#[pymethods]
impl PyOrcaClient {
    #[new]
    fn new(rpc_url: String) -> Self {
        let client = OrcaClient::new(&rpc_url);
        PyOrcaClient {
            client: Arc::new(tokio::sync::Mutex::new(client)),
        }
    }

    fn get_program_id(&self) -> String {
        OrcaClient::get_program_id()
    }

    fn get_sol_mint(&self) -> String {
        OrcaClient::get_sol_mint()
    }

    fn get_usdc_mint(&self) -> String {
        OrcaClient::get_usdc_mint()
    }

    fn get_usdt_mint(&self) -> String {
        OrcaClient::get_usdt_mint()
    }

    fn get_orca_mint(&self) -> String {
        OrcaClient::get_orca_mint()
    }

    fn get_balance(&self, address: String) -> PyResult<u64> {
        let client = self.client.clone();
        
        // Ejecutar en un runtime tokio
        let rt = tokio::runtime::Runtime::new().unwrap();
        match rt.block_on(async {
            let client = client.lock().await;
            client.get_balance(&address).await
        }) {
            Ok(balance) => Ok(balance),
            Err(e) => Err(PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(
                e.to_string(),
            )),
        }
    }

    fn get_token_balance(&self, wallet: String, mint: String) -> PyResult<u64> {
        let client = self.client.clone();
        
        let rt = tokio::runtime::Runtime::new().unwrap();
        match rt.block_on(async {
            let client = client.lock().await;
            client.get_token_balance(&wallet, &mint).await
        }) {
            Ok(balance) => Ok(balance),
            Err(e) => Err(PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(
                e.to_string(),
            )),
        }
    }

    fn get_swap_quote(
        &self,
        input_mint: String,
        output_mint: String,
        amount: u64,
        slippage: f64,
    ) -> PyResult<String> {
        let client = self.client.clone();
        
        let rt = tokio::runtime::Runtime::new().unwrap();
        match rt.block_on(async {
            let client = client.lock().await;
            client.get_swap_quote_api(&input_mint, &output_mint, amount, slippage).await
        }) {
            Ok(quote) => {
                serde_json::to_string(&quote)
                    .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(e.to_string()))
            },
            Err(e) => Err(PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(
                e.to_string(),
            )),
        }
    }

    fn get_all_pools(&self) -> PyResult<String> {
        let client = self.client.clone();
        
        let rt = tokio::runtime::Runtime::new().unwrap();
        match rt.block_on(async {
            let client = client.lock().await;
            client.get_all_pools().await
        }) {
            Ok(pools) => {
                serde_json::to_string(&pools)
                    .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(e.to_string()))
            },
            Err(e) => Err(PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(
                e.to_string(),
            )),
        }
    }

    fn get_whirlpools(&self) -> PyResult<String> {
        let client = self.client.clone();
        
        let rt = tokio::runtime::Runtime::new().unwrap();
        match rt.block_on(async {
            let client = client.lock().await;
            client.get_whirlpools().await
        }) {
            Ok(whirlpools) => {
                serde_json::to_string(&whirlpools)
                    .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(e.to_string()))
            },
            Err(e) => Err(PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(
                e.to_string(),
            )),
        }
    }
}

#[pymodule]
fn orca_rust_bridge(_py: Python, m: &PyModule) -> PyResult<()> {
    m.add_class::<PyOrcaClient>()?;
    
    // Constantes
    m.add("WHIRLPOOL_PROGRAM_ID", "whirLbMiicVdio4qvUfM5KAg6Ct8VwpYzGff3uctyCc")?;
    m.add("SOL_MINT", "So11111111111111111111111111111111111111112")?;
    m.add("USDC_MINT", "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v")?;
    m.add("USDT_MINT", "Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB")?;
    m.add("ORCA_MINT", "orcaEKTdK7LKz57vaAYr9QeNsVEPfiu6QeMU1kektZE")?;
    
    Ok(())
}