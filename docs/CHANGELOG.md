# Changelog

## [2.0.0] - 2025-11-02

### Major Reorganization

Complete project restructuring for better maintainability and contributor experience.

#### Added
- **New modular structure** under `app/` directory
  - `app/auth/` - Authentication module
  - `app/core/` - Core functionality
  - `app/pyvyos/` - VyOS API client library
  - `app/modules/` - Feature modules (interfaces, DHCP, NAT, firewall, dashboard, logs)
  - `app/static/` - Static assets
  - `app/templates/` - HTML templates
- **Test organization** - All tests now in `tests/` directory
- **Comprehensive documentation**
  - PROJECT_STRUCTURE.md - Detailed structure guide
  - CONTRIBUTING.md - Contributor guidelines
  - QUICK_REFERENCE.md - Quick lookup guide

#### Changed
- **Import paths** - All imports now use `app.*` paths
  - `from auth_utils import login_required` → `from app.auth import login_required`
  - `from config_manager import mark_config_dirty` → `from app.core import mark_config_dirty`
- **Template organization** - Removed nested `service/` directory, moved to `app/templates/`
- **Library location** - Moved pyvyos from root to `app/pyvyos/`

#### Removed
- **Duplicate directories** - Eliminated `/interfaces` and `/service/interfaces` duplication
- **Old structure** - Removed deprecated flat structure directories
- **Empty directories** - Removed `templates/partials/` and `templates/service/`

#### Fixed
- **Consistent module patterns** - All modules follow same structure
- **Clear separation of concerns** - Auth, core, and features properly separated
- **Professional organization** - Follows Flask and Python best practices

---

## Old to New File Mapping

| Old Location | New Location |
|-------------|-------------|
| `auth_utils.py` | `app/auth/decorators.py` |
| `config_manager.py` | `app/core/config_manager.py` |
| `pyvyos/` | `app/pyvyos/` |
| `service/interfaces/` | `app/modules/interfaces/` |
| `service/dhcp/` | `app/modules/dhcp/` |
| `service/nat/` | `app/modules/nat/` |
| `firewall/` | `app/modules/firewall/` |
| `dashboard/` | `app/modules/dashboard/` |
| `logs/` | `app/modules/logs/` |
| `static/` | `app/static/` |
| `templates/service/` | `app/templates/` |
| `test.py` | `tests/test.py` |

---

## Migration Notes

### No Breaking Changes for Users
- Same `.env` configuration
- Same Docker setup
- Same API endpoints
- Same functionality
- Same template structure

### For Developers
Update your imports if you have custom modifications:

**Before:**
```python
from auth_utils import login_required
from config_manager import mark_config_dirty
from interfaces.util import is_valid_cidr
```

**After:**
```python
from app.auth import login_required
from app.core import mark_config_dirty
from app.modules.interfaces.utils import is_valid_cidr
```

See [PROJECT_STRUCTURE.md](PROJECT_STRUCTURE.md) for details.

---

## Previous Versions

### [1.0.0] - 2025-10-23
- Initial release with flat structure
- Interface management
- DHCP configuration
- Firewall rules and zones
- NAT management
- Dashboard
- System logs
