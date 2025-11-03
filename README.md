# Vyerwall-GUI for use with VyOS
## Disclaimer
The Vyerwall-GUI project is not affiliated with VyOS in any way. It is a wholly separate project to build a community tool that helps to visually build and manage firewall specific configurations for VyOS firewalls. This project is not owned by VyOS.io, or Sentrium S.L., nor does it seek to appear to be an official project, product or partner of the aforementioned.

## Overview
Vyerwall-GUI is a Flask-based management interface that talks to a VyOS router through the official API. It provides dashboards, interface configuration helpers, DHCP utilities, log browsing, and firewall tooling so you can operate your VyOS deployment without memorising the CLI.

## Feature Highlights
- Live dashboard with auto-refreshing CPU, memory, storage, service, and interface data.
- Interfaces view for managing ethernet, VLAN, NAT, and zone assignments.
- DHCP, firewall rule, and log blueprints grouped into dedicated pages.
- Session-protected login with simple credential configuration.
- Optional Docker image for quick deployment.

## Requirements
- Python 3.12
- Access to a VyOS device reachable via the VyOS HTTP API.
- The Python dependencies listed in `requirements.txt`.
- (Optional) Docker 24+ for containerised usage.

## Quick Start (Docker)
1. Clone the repository and enter the project directory:
   ```bash
   git clone https://github.com/xTITUSMAXIMUSX/vyerwall-gui.git
   cd vyerwall-gui
   ```
2. Copy `.env` and update values to match your VyOS appliance and desired credentials.
3. Build the container:
   ```bash
   docker build -t vyerwall-gui .
   ```
4. Run the container, providing the environment file:
   ```bash
   docker run --env-file .env -p 5000:5000 --name vyerwall-gui vyerwall-gui
   ```
5. Browse to `http://<host>:5000` and log in with the credentials defined in `.env`.

## Local Development Setup
1. Create and activate a virtual environment (optional but recommended):
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Configure environment variables (see below).
4. Run the development server:
   ```bash
   python main.py
   ```
5. The app listens on `http://0.0.0.0:5000` by default. Use `FLASK_DEBUG=1` or adjust `main.py` if you want live reload.

## Environment Configuration
The application reads connection details and login credentials from `.env` using `python-dotenv`. Populate at least the following keys:

```env
VYDEVICE_HOSTNAME="192.0.2.1"
VYDEVICE_APIKEY="vyos-api-token"
VYDEVICE_PORT="443"
VYDEVICE_PROTOCOL="https"
VYDEVICE_VERIFY_SSL="false"   # set to "true" when using valid certificates

USERNAME="admin"
PASSWORD="supersecret"
```

If you prefer runtime export instead of a `.env` file, set these variables in your shell before starting the app.

## Project Structure
The project follows a modular architecture for better organization and maintainability:

- `main.py` — Application entry point, blueprint registration, and VyOS device initialization
- `app/` — Main application package containing all modules
  - `auth/` — Authentication and session management
  - `core/` — Core functionality (config state tracking)
  - `modules/` — Feature modules (dashboard, interfaces, DHCP, NAT, firewall, logs)
  - `lib/` — Third-party integrations (pyvyos API client)
  - `static/` — CSS, JavaScript, and other static assets
  - `templates/` — Jinja2 HTML templates
- `tests/` — Test suite and debug scripts
- `docs/` — Project documentation

For detailed information about the project structure and development guidelines, see [docs/PROJECT_STRUCTURE.md](docs/PROJECT_STRUCTURE.md).

## Development Tips
- The `/get-*-usage` endpoints are polled from the dashboard every 3 seconds; ensure your VyOS device can respond within that interval.
- When running locally without Docker, keep a virtual environment active so dependencies stay isolated.
- Ignore generated files (`bin/`, `lib/`, `__pycache__/`, etc.) via the included `.gitignore`.

## Troubleshooting
- **Authentication errors** — Validate the API key and protocol in `.env`. VyOS must have its HTTPS API enabled.
- **SSL issues** — Set `VYDEVICE_VERIFY_SSL="true"` only when the appliance presents a trusted certificate.
- **Connection refused** — Confirm the VyOS API is reachable from the host running the GUI and that any firewalls permit the traffic.

## Contributing
Issues and pull requests are welcome. Open a discussion if you plan major changes so we can coordinate around the roadmap.

## License
See `LICENSE` for licensing details (if present in your fork or upstream repository).
