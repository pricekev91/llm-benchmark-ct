# LLM Benchmark Tool - Infrastructure Plan

This repository hosts the architecture and code for the LLM Benchmark tool.

## 🚀 Overview
The tool allows users to configure, run, and analyze benchmarks against various Large Language Models (LLMs) and APIs.

## ⚙️ Setup and Deployment
Follow the instructions in `deploy-llm-benchmark-ct.sh` to set up the environment.

### Prerequisites
- Docker and Docker Compose
- Python 3.10+
- Node.js and npm

## 💾 Data Persistence
Data is persisted using SQLite in `/volumes/db/db.sqlite` and endpoint configurations are stored in `/volumes/configs/`.

## 🤝 Roadmap
- **Phase 0:** Architecture Plan (Complete)
- **Phase 1:** Scaffolding & Deployment (Current)
- **Phase 2:** Benchmark Engine & Data Capture (Next)
- ...