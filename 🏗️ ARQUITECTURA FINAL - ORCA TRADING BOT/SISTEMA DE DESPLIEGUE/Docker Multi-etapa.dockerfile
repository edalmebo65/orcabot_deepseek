# Dockerfile
# Build stage - Rust
FROM rust:1.70 as rust-builder
WORKDIR /app/rust
COPY rust/Cargo.toml rust/Cargo.lock ./
COPY rust/src ./src
RUN cargo build --release

# Build stage - Python
FROM python:3.10-slim as python-builder
WORKDIR /app
COPY requirements.txt .
RUN pip install --user -r requirements.txt

# Final stage
FROM python:3.10-slim
WORKDIR /app

# Copiar artefactos Rust
COPY --from=rust-builder /app/rust/target/release/liborca_rust_bridge.so ./python/

# Copiar Python
COPY --from=python-builder /root/.local /root/.local
COPY python ./python
COPY config ./config
COPY scripts ./scripts

ENV PATH=/root/.local/bin:$PATH
ENV PYTHONPATH=/app/python:$PYTHONPATH

CMD ["python", "python/main.py"]