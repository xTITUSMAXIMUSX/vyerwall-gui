# Quick Reference - New Project Structure

## 📍 Where to Find Things

| What You Need | Location |
|--------------|----------|
| **Application entry point** | `main.py` |
| **Authentication** | `app/auth/decorators.py` |
| **Config state tracking** | `app/core/config_manager.py` |
| **VyOS API client** | `app/lib/pyvyos/` |
| **Interface management** | `app/modules/interfaces/` |
| **DHCP management** | `app/modules/dhcp/` |
| **NAT rules** | `app/modules/nat/` |
| **Firewall rules** | `app/modules/firewall/rules/` |
| **Firewall zones** | `app/modules/firewall/zone/` |
| **Dashboard** | `app/modules/dashboard/` |
| **Logs** | `app/modules/logs/` |
| **HTML templates** | `app/templates/` |
| **JavaScript** | `app/static/js/` |
| **CSS** | `app/static/css/` |
| **Tests** | `tests/` |
| **Documentation** | `docs/` |

## 🔍 Common Tasks

### Adding a New Feature Module

```bash
# 1. Create directory
mkdir -p app/modules/your_feature

# 2. Create files
touch app/modules/your_feature/{__init__.py,views.py,utils.py}

# 3. Edit __init__.py
cat > app/modules/your_feature/__init__.py << 'EOF'
"""Your feature description"""
from .views import your_bp
__all__ = ['your_bp']
EOF

# 4. Create blueprint in views.py
# 5. Register in main.py
```

### Importing Code

```python
# Authentication
from app.auth import login_required

# Config manager
from app.core import mark_config_dirty, is_config_dirty

# From another module
from app.modules.interfaces.utils import is_valid_cidr

# Within same module (relative)
from .utils import helper_function
from .dhcp import build_dhcp_config
```

### Running the Application

```bash
# Activate virtual environment
source bin/activate

# Run application
python main.py

# Access at: http://localhost:5000
```

### Testing Imports

```bash
source bin/activate
python3 -c "from app.modules.interfaces import interfaces_bp; print('OK')"
```

## 📋 Module Structure Pattern

Every feature module follows this pattern:

```
app/modules/feature_name/
├── __init__.py        # Exports: from .views import feature_bp
├── views.py           # Blueprint with routes
└── utils.py           # Helper functions (optional)
```

## 🎯 Import Rules

1. **Use absolute imports** from outside the module:
   ```python
   from app.modules.interfaces import interfaces_bp
   ```

2. **Use relative imports** within the module:
   ```python
   from .utils import function_name
   ```

3. **Always import from app.auth and app.core**:
   ```python
   from app.auth import login_required
   from app.core import mark_config_dirty
   ```

## 📚 Documentation Files

| File | Purpose |
|------|---------|
| `PROJECT_STRUCTURE.md` | Detailed structure guide |
| `CONTRIBUTING.md` | How to contribute |
| `CHANGELOG.md` | Old → New mappings |
| `QUICK_REFERENCE.md` | This file |

## 🚀 Common Commands

```bash
# Activate virtual environment
source bin/activate

# Install dependencies
pip install -r requirements.txt

# Run application
python main.py

# Run tests
python -m pytest tests/

# Check syntax
python3 -m py_compile main.py

# Test specific import
python3 -c "from app.modules.interfaces import interfaces_bp"
```

## 🔧 Troubleshooting

**Import errors?**
- Check you're using `app.*` paths
- Verify virtual environment is activated
- Ensure `__init__.py` exists in directories

**Module not found?**
- Verify file exists in `app/modules/`
- Check `__init__.py` exports the blueprint
- Use relative imports within modules

**Templates not found?**
- Templates are in `app/templates/`
- main.py sets `template_folder='app/templates'`

## 🎨 Code Style

```python
# Function with type hints and docstring
def validate_network(address: str) -> Tuple[bool, Optional[str]]:
    """
    Validate network address.

    Args:
        address: IP address in CIDR notation

    Returns:
        Tuple of (is_valid, error_message)
    """
    # Implementation
    pass
```

## 📝 Git Workflow

```bash
# Create feature branch
git checkout -b feature/your-feature

# Make changes
# ...

# Commit
git add .
git commit -m "Add feature: description"

# Push
git push origin feature/your-feature

# Create PR on GitHub
```

## ✅ Pre-Commit Checklist

- [ ] Code follows existing patterns
- [ ] Imports use correct paths (`app.*`)
- [ ] Functions have docstrings
- [ ] No console.log in production code
- [ ] Templates follow existing structure
- [ ] Tests added (if applicable)
- [ ] Documentation updated

## 🆘 Getting Help

- Read `docs/PROJECT_STRUCTURE.md`
- Read `docs/CONTRIBUTING.md`
- Check GitHub issues
- Open new issue with details

---

**Quick Tip:** Keep this reference handy while developing!
