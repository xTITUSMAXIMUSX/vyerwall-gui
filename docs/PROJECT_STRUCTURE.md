# VyerWall GUI - Project Structure

This document explains the organization of the VyerWall GUI codebase.

## Directory Structure

```
vyerwall-gui/
├── app/                         # Main application package
│   ├── __init__.py
│   ├── auth/                    # Authentication module
│   │   ├── __init__.py
│   │   └── decorators.py        # login_required decorator
│   │
│   ├── core/                    # Core functionality
│   │   ├── __init__.py
│   │   └── config_manager.py    # Configuration state management
│   │
│   │
│   ├── modules/                 # Feature modules
│   │   ├── __init__.py
│   │   │
│   │   ├── dashboard/           # System dashboard
│   │   │   ├── __init__.py
│   │   │   └── dashboard.py
│   │   │
│   │   ├── interfaces/          # Network interface management
│   │   │   ├── __init__.py
│   │   │   ├── views.py         # Routes and API endpoints
│   │   │   ├── utils.py         # Utility functions
│   │   │   ├── dhcp.py          # DHCP configuration helpers
│   │   │   ├── nat.py           # NAT configuration helpers
│   │   │   ├── zone.py          # Firewall zone helpers
│   │   │   ├── device.py        # Device configuration helpers
│   │   │   ├── firewall.py      # Firewall helpers
│   │   │   └── constants.py     # Constants
│   │   │
│   │   ├── dhcp/                # DHCP server management
│   │   │   ├── __init__.py
│   │   │   ├── views.py
│   │   │   └── utils.py
│   │   │
│   │   ├── nat/                 # NAT management
│   │   │   ├── __init__.py
│   │   │   └── views.py
│   │   │
│   │   ├── firewall/            # Firewall management
│   │   │   ├── __init__.py
│   │   │   ├── common.py
│   │   │   ├── rules/           # Firewall rules
│   │   │   │   ├── __init__.py
│   │   │   │   ├── views.py
│   │   │   │   └── utils.py
│   │   │   └── zone/            # Firewall zones
│   │   │       ├── __init__.py
│   │   │       ├── views.py
│   │   │       └── utils.py
│   │   │
│   │   └── logs/                # System logs
│   │       ├── __init__.py
│   │       └── logs.py
│   │
│   ├── static/                  # Static files (CSS, JS, images)
│   │   └── js/
│   │       ├── interfaces/
│   │       │   ├── index.js
│   │       │   ├── utils.js
│   │       │   ├── domCache.js
│   │       │   ├── addInterfaceModal.js
│   │       │   ├── editModal.js
│   │       │   ├── vlanModal.js
│   │       │   ├── deleteModal.js
│   │       │   ├── powerControls.js
│   │       │   └── unassignZone.js
│   │       ├── firewall/
│   │       │   ├── index.js
│   │       │   ├── constants.js
│   │       │   ├── utils.js
│   │       │   ├── state.js
│   │       │   ├── controller.js
│   │       │   └── controller/
│   │       │       ├── api.js
│   │       │       ├── forms.js
│   │       │       └── view.js
│   │       ├── dhcp.js
│   │       └── nat.js
│   │
│   └── templates/               # Jinja2 templates
│       ├── base.html
│       ├── login.html
│       ├── dashboard.html
│       ├── interfaces/
│       ├── dhcp/
│       ├── nat/
│       ├── firewall/
│       ├── logs/
│       ├── partials/            # Shared template components
│       └── service/             # Service-specific templates
│
├── tests/                       # Test suite
│   ├── __init__.py
│   ├── test_interfaces.py
│   └── debug/                   # Debug scripts
│       └── debug_list_error.py
│
├── docs/                        # Documentation
│   └── PROJECT_STRUCTURE.md     # This file
│
├── scripts/                     # Utility scripts
│   └── update_imports.sh
│
├── main.py                      # Application entry point
├── requirements.txt             # Python dependencies
├── .env                         # Environment variables (not in git)
├── .gitignore                   # Git ignore rules
├── Dockerfile                   # Docker configuration
├── README.md                    # Project README
└── LICENSE                      # Project license
```

## Module Organization

### Authentication (`app/auth/`)
Handles user authentication and session management.

**Files:**
- `decorators.py`: Contains the `@login_required` decorator for protecting routes

### Core (`app/core/`)
Core application functionality that's used across modules.

**Files:**
- `config_manager.py`: Tracks unsaved configuration changes
  - `mark_config_dirty()`: Mark configuration as modified
  - `mark_config_clean()`: Mark configuration as saved
  - `is_config_dirty()`: Check if there are unsaved changes

### Modules (`app/modules/`)
Feature-specific functionality organized by domain.

Each module follows a consistent structure:
- `__init__.py`: Module exports
- `views.py`: Flask blueprint with routes and API endpoints
- `utils.py`: Helper functions specific to the module

#### Interfaces Module
The most complex module, handling network interface configuration.

**Key Files:**
- `views.py`: Main routes for interface management
- `utils.py`: Network validation and utility functions
  - `is_valid_network_prefix()`: Validates network addresses
  - `is_valid_cidr()`: CIDR notation validation
  - `extract_configured_interfaces()`: Parse VyOS config
- `dhcp.py`: DHCP configuration builders
- `nat.py`: NAT rule management
- `zone.py`: Firewall zone integration

## Import Patterns

### Importing Authentication
```python
from app.auth import login_required
```

### Importing Core Functionality
```python
from app.core import mark_config_dirty, is_config_dirty
```

### Importing Blueprints
```python
from app.modules.interfaces import interfaces_bp
from app.modules.firewall import rules_bp, zone_bp
```

### Within a Module (Relative Imports)
```python
# In app/modules/interfaces/views.py
from .utils import is_valid_cidr
from .dhcp import build_dhcp_paths
```

## Adding a New Module

To add a new feature module:

1. Create directory: `app/modules/your_module/`
2. Create `__init__.py`:
   ```python
   """
   Your module description
   """
   from .views import your_bp

   __all__ = ['your_bp']
   ```
3. Create `views.py` with Flask blueprint:
   ```python
   from flask import Blueprint
   from app.auth import login_required

   your_bp = Blueprint("your_module", __name__, url_prefix="/your-prefix")

   @your_bp.route("/")
   @login_required
   def index():
       return render_template("your_module/index.html")
   ```
4. Register blueprint in `main.py`:
   ```python
   from app.modules.your_module import your_bp
   app.register_blueprint(your_bp)
   ```

## Testing

Run tests from the project root:
```bash
python -m pytest tests/
```

## Development Setup

1. Create virtual environment:
   ```bash
   python3 -m venv .
   source bin/activate
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Configure environment:
   ```bash
   cp .env.example .env
   # Edit .env with your settings
   ```

4. Run application:
   ```bash
   python main.py
   ```

## Contributing

When contributing to this project:

1. Follow the existing module structure
2. Use relative imports within modules
3. Import from `app.auth` and `app.core` for cross-module dependencies
4. Add tests for new functionality in `tests/`
5. Update this documentation if adding new modules

## Migration Notes

This structure was reorganized from a flat structure to improve:
- **Discoverability**: Clear hierarchy makes it easy to find code
- **Maintainability**: Related code is grouped together
- **Scalability**: Easy to add new features following established patterns
- **Testing**: Isolated modules are easier to test
