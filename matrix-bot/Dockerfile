# =============================================================================
# a0-matrix Bot — Multi-stage Rust build
# =============================================================================

# --- Stage 1: Build ---
FROM rust:1.86-slim-bookworm AS builder

RUN apt-get update && apt-get install -y --no-install-recommends \
    pkg-config libssl-dev ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /build

# Copy manifests first for layer caching
COPY rust/Cargo.toml rust/Cargo.lock* ./

# Create dummy src for dependency caching
RUN mkdir -p src/bin && \
    echo 'fn main() {}' > src/main.rs && \
    echo 'fn main() {}' > src/bin/set_display_name.rs && \
    cargo build --release 2>/dev/null || true && \
    rm -rf src

# Copy real source
COPY rust/src/ ./src/

# Force cargo to detect changed source files and rebuild (not reuse dummy binary)
RUN find src -name '*.rs' -exec touch {} + && cargo build --release

# --- Stage 2: Runtime ---
FROM debian:bookworm-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy binaries from builder
COPY --from=builder /build/target/release/matrix-bot-rust /app/matrix-bot-rust
COPY --from=builder /build/target/release/set-display-name-rust /app/set-display-name-rust

# Create data directory for room_contexts.json persistence
RUN mkdir -p /app/data

ENV RUST_LOG=info

ENTRYPOINT ["/app/matrix-bot-rust"]
