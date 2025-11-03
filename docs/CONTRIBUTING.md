# Contributing to VyerWall GUI

Thank you for your interest in contributing to VyerWall GUI! This document provides guidelines and information for contributors.

## Code of Conduct

Be respectful, constructive, and professional in all interactions.

## Getting Started

### Prerequisites

- Python 3.12 or higher
- Git
- Access to a VyOS device for testing (or ability to set one up)
- Familiarity with Flask, Jinja2, and JavaScript

### Development Setup

1. **Fork and clone the repository:**
   ```bash
   git clone https://github.com/YOUR_USERNAME/vyerwall-gui.git
   cd vyerwall-gui
   ```

2. **Create a virtual environment:**
   ```bash
   python3 -m venv .
   source bin/activate  # On Windows: bin\Scripts\activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment:**
   ```bash
   cp .env.example .env
   # Edit .env with your VyOS device details
   ```

5. **Run the application:**
   ```bash
   python main.py
   ```

## Project Structure

VyerWall GUI follows a modular architecture. Please read [PROJECT_STRUCTURE.md](PROJECT_STRUCTURE.md) to understand:
- Where to place new code
- Import patterns to follow
- Module organization conventions

## Making Changes

### Branch Naming

Use descriptive branch names:
- `feature/add-vpn-management` - New features
- `fix/interface-validation-bug` - Bug fixes
- `docs/update-readme` - Documentation updates
- `refactor/simplify-nat-logic` - Code refactoring

### Coding Standards

#### Python Code

- **PEP 8 Compliance**: Follow [PEP 8](https://pep8.org/) style guidelines
- **Type Hints**: Use type hints for function parameters and return values
  ```python
  def is_valid_cidr(address: str) -> bool:
      """Check if address is valid CIDR notation."""
      ...
  ```
- **Docstrings**: Add docstrings to all functions, classes, and modules
  ```python
  def build_nat_rule(interface: str, network: str) -> List[str]:
      """
      Build NAT rule configuration paths.

      Args:
          interface: Outbound interface name
          network: Source network in CIDR notation

      Returns:
          List of VyOS configuration paths
      """
      ...
  ```
- **Error Handling**: Always handle exceptions appropriately
  ```python
  try:
      result = device.configure_set(path)
  except Exception as exc:
      current_app.logger.error(f"Failed to configure: {exc}")
      return {"status": "error", "message": str(exc)}, 500
  ```

#### JavaScript Code

- **ES6+ Syntax**: Use modern JavaScript (const/let, arrow functions, async/await)
- **Module Pattern**: Export/import functions instead of global scope
  ```javascript
  // Good
  export function validateIpAddress(ip) { ... }

  // Avoid
  function validateIpAddress(ip) { ... }  // Global
  ```
- **Error Handling**: Use try/catch for async operations
  ```javascript
  try {
      const result = await requestJson('/api/endpoint');
      // Handle result
  } catch (error) {
      console.error('API call failed:', error);
      alert('Operation failed');
  }
  ```

#### HTML/Templates

- **Semantic HTML**: Use appropriate HTML5 elements
- **Accessibility**: Include ARIA labels and proper form labels
- **Consistent Styling**: Follow existing TailwindCSS patterns

### Import Organization

Follow these import patterns consistently:

```python
# Standard library imports
import os
import re
from typing import List, Optional

# Third-party imports
from flask import Blueprint, request, jsonify

# Application imports - use absolute imports from app/
from app.auth import login_required
from app.core import mark_config_dirty

# Relative imports within the same module
from .utils import validate_network
from .dhcp import build_dhcp_config
```

### Adding New Features

#### 1. Plan Your Feature

- Open an issue to discuss the feature before starting work
- Get feedback on the approach
- Clarify requirements and scope

#### 2. Create a New Module (if needed)

If adding a major feature, create a new module:

```bash
mkdir -p app/modules/your_feature
touch app/modules/your_feature/{__init__.py,views.py,utils.py}
```

Follow the pattern in existing modules (see [PROJECT_STRUCTURE.md](PROJECT_STRUCTURE.md)).

#### 3. Add Tests

Create tests for your feature:

```python
# tests/test_your_feature.py
def test_your_function():
    """Test description."""
    result = your_function(test_input)
    assert result == expected_output
```

#### 4. Update Documentation

- Update relevant documentation files
- Add docstrings to all new functions
- Update PROJECT_STRUCTURE.md if adding new modules

### Submitting Changes

#### 1. Commit Messages

Write clear, descriptive commit messages:

```
Add network prefix validation to interface management

- Implement is_valid_network_prefix() function
- Add validation modal for invalid prefixes
- Update interface edit/create flows to validate before submission
- Add comprehensive tests for various prefix lengths

Fixes #123
```

Format:
- First line: Brief summary (50 chars or less)
- Blank line
- Detailed description with bullet points
- Reference related issues

#### 2. Pull Request Process

1. **Update your fork:**
   ```bash
   git fetch upstream
   git rebase upstream/master
   ```

2. **Push your changes:**
   ```bash
   git push origin your-branch-name
   ```

3. **Create Pull Request:**
   - Go to GitHub and create a PR from your branch
   - Fill out the PR template
   - Link related issues
   - Add screenshots for UI changes

4. **PR Description Should Include:**
   - What changes were made and why
   - How to test the changes
   - Any breaking changes
   - Screenshots/GIFs for UI changes

#### 3. Code Review

- Address review comments promptly
- Keep discussions focused and professional
- Update code based on feedback
- Squash commits if requested

## Testing

### Manual Testing

1. Test all affected functionality
2. Test on different screen sizes (for UI changes)
3. Verify no console errors
4. Check network tab for failed requests

### Automated Testing

Run the test suite before submitting:

```bash
python -m pytest tests/
```

## Common Pitfalls

### ❌ Don't Do This

```python
# Hard-coded values
if interface == "eth0":
    ...

# Ignoring errors
try:
    risky_operation()
except:
    pass

# Global variables in modules
current_interface = None
```

### ✅ Do This Instead

```python
# Configuration-driven
if interface == get_wan_interface():
    ...

# Proper error handling
try:
    risky_operation()
except Exception as exc:
    logger.error(f"Operation failed: {exc}")
    return error_response(str(exc))

# Pass data through function parameters
def process_interface(interface: str) -> Dict[str, Any]:
    ...
```

## Getting Help

- **Questions**: Open a GitHub discussion
- **Bugs**: Open an issue with reproduction steps
- **Features**: Open an issue to discuss before implementing

## License

By contributing, you agree that your contributions will be licensed under the same license as the project.

## Recognition

Contributors will be recognized in the project README and release notes.

Thank you for contributing to VyerWall GUI!
