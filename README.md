# OpenMFDA: Open-Source Microfluidic Design Automation

OpenMFDA is a hardware-description-language (HDL) based toolchain for the automated design, simulation, and 3D printing of microfluidic devices. By bridging the gap between Electronic Design Automation (EDA) and Bioengineering, it allows researchers to synthesize complex fluidic circuits from Verilog-AMS specifications.

## 🚀 Quick Start (Cross-Platform)

This project is fully containerized. To ensure compatibility across Windows, macOS, and Linux, we use **Docker** and **VS Code Dev Containers**.

### Prerequisites
* [Docker Desktop](https://www.docker.com/products/docker-desktop/)
* [VS Code](https://code.visualstudio.com/) with the **Dev Containers** extension.

### Installation
1. **Clone the repo:**
   ```bash
   git clone https://github.com/rennerjones/openmfda_flow.git
   cd openmfda_flow
   ```

2. **Open in VS Code:**
   ```bash
   code .
   ```

3. **Launch Container:**
   When prompted, click **"Reopen in Container"**. This builds the Linux environment with all EDA tools (Xyce, OpenROAD, Python) pre-installed.

## 🛠️ Project Structure

* `/src`: Core Python logic for routing and placement.
* `/sim`: Xyce simulation netlists and verification scripts.
* `/cad`: 3D geometry generation modules (STL/GDS).
* `/tests`: Unit tests for fluidic logic gates.

## 🧪 Development Workflow

Before pushing code, run the local cleanup and test suite:

1. **Clean Workspace:**
   ```bash
   python3 scripts/clean_mfda.py
   ```

2. **Run Simulations:**
   ```bash
   python3 main.py --simulate
   ```

## 🏗️ CI/CD Pipeline

This repository uses **GitHub Actions** to automatically verify:

* **Multi-Architecture Support:** Builds are tested on both AMD64 (Standard PC) and ARM64 (Apple Silicon).
* **Simulation Integrity:** Automated Xyce netlist verification on every push to `main`.

## 🎓 Academic Context

Developed at the **University of Utah**. OpenMFDA is part of ongoing research into Microfluidic Design Automation (MFDA) for 3D-printed medical devices and bio-engineering applications.

---

**Maintained by:** Renner Jones
**License:** MIT
