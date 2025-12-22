#Stage 1: The Build Environment
FROM gcc:13 AS builder

# Install Cmake and Build Tools
RUN apt-get update && apt-get install -y \
    cmake \
    ninja-build \
    && rm - rf /var/lib/apt/list/*

WORKDIR /app

# Copy soruce code
COPY . .

# Build the project
RUN cmake -B build -G Ninja -DCMAKE_BUILD_TYPE=Release
RUN cmake --build build

# Stage 2: The Production Runtime(Lightweight)
# use a distroless or minimal image for security and speed
FROM ubuntu:22.04 AS runtime

# Install only runtime dependencies
RUN apt-get update && apt-get install -y \
    libstdc++6 \
    && rm -rf /var/lib/apt/list/*

WORKDIR /app

# Copy only the binary from the builder stage
COPY --from=builder /app/build/chronos_engine /app/chronos_engine

#Run the engine
CMD ["./chronos_engine"]