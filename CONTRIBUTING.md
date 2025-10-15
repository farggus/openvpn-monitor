# Contributing to OpenVPN Monitor

Thank you for considering contributing to OpenVPN Monitor! We welcome contributions from the community and are grateful for your support.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Workflow](#development-workflow)
- [How to Contribute](#how-to-contribute)
- [Coding Standards](#coding-standards)
- [Testing Guidelines](#testing-guidelines)
- [Documentation](#documentation)
- [Submitting Changes](#submitting-changes)
- [Community](#community)

## Code of Conduct

By participating in this project, you agree to maintain a respectful and collaborative environment. We expect all contributors to:

- Use welcoming and inclusive language
- Respect differing viewpoints and experiences
- Accept constructive criticism gracefully
- Focus on what is best for the community
- Show empathy towards other community members

## Getting Started

### Prerequisites

Before you begin contributing, ensure you have:

- **Git** installed on your local machine
- **Python 3.11+** for development
- **Docker 24+** and **Docker Compose v2** for containerized testing
- Basic understanding of Flask, OpenVPN, and web development
- A GitHub account

### Setting Up Your Development Environment

1. **Fork the Repository**

   Click the "Fork" button at the top right of the [repository page](https://github.com/farggus/openvpn-monitor).

2. **Clone Your Fork**

   ```bash
   git clone https://github.com/YOUR_USERNAME/openvpn-monitor.git
   cd openvpn-monitor
   ```

3. **Add Upstream Remote**

   ```bash
   git remote add upstream https://github.com/farggus/openvpn-monitor.git
   ```

4. **Create Python Virtual Environment**

   ```bash
   python3 -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   pip install --upgrade pip
   pip install -r requirements.txt
   pip install -r requirements-dev.txt
   ```

5. **Set Up Environment Variables**

   ```bash
   export OPENVPN_STATUS_LOG=/var/log/openvpn/status.log
   export OPENVPN_HISTORY_LOG=$(pwd)/data/session_history.json
   export OPENVPN_ACTIVE_SESSIONS=$(pwd)/data/active_sessions.json
   export OPENVPN_SERVER_STATUS=$(pwd)/data/server_status.json
   export OPENVPN_TRAFFIC_METRICS=$(pwd)/data/traffic_metrics.json
   export OPENVPN_MONITOR_TZ=Europe/Bucharest
   mkdir -p data
   ```

6. **Verify Installation**

   ```bash
   pytest
   ```

## Development Workflow

### Branching Strategy

- **main** - Stable production-ready code
- **feature/your-feature-name** - New features or enhancements
- **bugfix/issue-description** - Bug fixes
- **docs/documentation-update** - Documentation improvements

### Creating a Branch

```bash
git checkout main
git pull upstream main
git checkout -b feature/your-feature-name
```

### Keeping Your Branch Updated

```bash
git fetch upstream
git rebase upstream/main
```

## How to Contribute

### Reporting Bugs

Before creating a bug report, please:

1. **Check existing issues** to avoid duplicates
2. **Use the latest version** to confirm the bug still exists
3. **Gather information**: OS, Python version, Docker version, error logs

When creating a bug report, include:

- **Clear title** describing the issue
- **Steps to reproduce** the problem
- **Expected behavior** vs actual behavior
- **Environment details** (OS, versions, configuration)
- **Logs and screenshots** if applicable
- **Minimal test case** if possible

### Suggesting Enhancements

Enhancement suggestions are tracked as GitHub issues. When creating an enhancement suggestion:

- **Use a clear descriptive title**
- **Provide detailed explanation** of the proposed feature
- **Explain why this enhancement would be useful** to most users
- **List any alternatives** you've considered
- **Include mockups or examples** if applicable

### Areas for Contribution

We welcome contributions in these areas:

#### 1. Core Features

- **Parser improvements** (`app/parser.py`) - Handle edge cases, improve performance
- **API endpoints** (`app/routes.py`) - New endpoints or enhancements
- **Traffic analytics** (`app/traffic_collector.py`) - Advanced metrics, visualizations
- **History management** (`app/history_manager.py`) - Archival improvements, data compression

#### 2. Frontend Development

- **UI/UX improvements** - Better layouts, responsiveness, accessibility
- **Charts and visualizations** - Chart.js enhancements, new chart types
- **Map features** - Leaflet map improvements, clustering, custom markers
- **Performance** - Reduce page load time, optimize JavaScript

#### 3. Internationalization

- **New language translations** - Add support for additional languages
- **Translation improvements** - Fix or improve existing translations
- **Translation tools** - Scripts to help with translation management

See [I18N.md](translations/I18N.md) for translation guidelines.

#### 4. Testing

- **Unit tests** - Increase test coverage for core modules
- **Integration tests** - API endpoint testing
- **End-to-end tests** - Full workflow testing
- **Mock data** - Create realistic test scenarios

#### 5. Documentation

- **Code comments** - Improve inline documentation
- **API documentation** - Document request/response formats
- **Tutorials** - Step-by-step guides for specific use cases
- **Architecture diagrams** - Visual documentation of system design

#### 6. DevOps and Infrastructure

- **Docker improvements** - Optimize image size, build time
- **CI/CD** - GitHub Actions workflows for testing and deployment
- **Monitoring** - Health check endpoints, metrics collection
- **Performance** - Caching strategies, database optimization

## Coding Standards

### Python Style Guide

We follow **PEP 8** with some modifications:

- **Line length**: 88 characters (Black default)
- **Indentation**: 4 spaces (no tabs)
- **Quotes**: Double quotes for strings
- **Imports**: Grouped and sorted (stdlib, third-party, local)

### Code Formatting

We use **Black** for automatic code formatting:

```bash
black .
```

### Linting

We use **flake8** for linting:

```bash
flake8
```

Configuration is in `.flake8` file.

### Python Best Practices

- **Type hints** - Use type annotations for function signatures
- **Docstrings** - Document functions, classes, and modules
- **Error handling** - Use try/except blocks with specific exceptions
- **Logging** - Use Python's logging module instead of print statements
- **File locking** - Always use context managers and file locks for file operations
- **Atomic updates** - Use temp files and `os.replace()` for file writes

### Example Code Style

```python
from typing import Dict, List, Optional
import json
import fcntl


def parse_client_data(status_log: str) -> Dict[str, List[Dict]]:
    """
    Parse OpenVPN status log and extract client information.

    Args:
        status_log: Path to the OpenVPN status.log file

    Returns:
        Dictionary containing client data with 'active' and 'disconnected' keys

    Raises:
        FileNotFoundError: If status log doesn't exist
        ValueError: If status log format is invalid
    """
    try:
        with open(status_log, "r") as f:
            fcntl.flock(f, fcntl.LOCK_SH)
            data = f.read()
            fcntl.flock(f, fcntl.LOCK_UN)

        # Process data...
        return {"active": [], "disconnected": []}

    except FileNotFoundError as e:
        raise FileNotFoundError(f"Status log not found: {status_log}") from e
```

### JavaScript Style Guide

- **ES6+ syntax** - Use modern JavaScript features
- **Const/let** - Use `const` by default, `let` when needed, avoid `var`
- **Arrow functions** - Prefer arrow functions for callbacks
- **Template literals** - Use backticks for string interpolation
- **Semicolons** - Always use semicolons

### HTML/CSS Guidelines

- **Bootstrap 5** - Use Bootstrap classes for consistency
- **Responsive design** - Test on mobile, tablet, and desktop
- **Accessibility** - Use semantic HTML and ARIA labels
- **Performance** - Minimize CSS and JavaScript

## Testing Guidelines

### Running Tests

Run all tests:

```bash
pytest
```

Run specific test file:

```bash
pytest tests/test_parser.py
```

Run with coverage:

```bash
pytest --cov=app --cov-report=html
```

### Writing Tests

Tests should be:

- **Isolated** - No dependencies between tests
- **Fast** - Mock external services and file I/O
- **Readable** - Clear test names describing what is being tested
- **Comprehensive** - Cover edge cases and error conditions

### Test Structure

```python
import pytest
from app.parser import parse_status_log


class TestStatusParser:
    """Tests for OpenVPN status log parser."""

    def test_parse_empty_log(self, tmp_path):
        """Test parsing an empty status log file."""
        log_file = tmp_path / "status.log"
        log_file.write_text("")

        result = parse_status_log(str(log_file))

        assert result["clients"] == []
        assert result["total_traffic"] == 0

    def test_parse_single_client(self, tmp_path):
        """Test parsing status log with one active client."""
        log_file = tmp_path / "status.log"
        log_file.write_text("""
            OpenVPN CLIENT LIST
            Common Name,Real Address,Bytes Received,Bytes Sent,Connected Since
            client1,192.168.1.100:54321,1234567,7654321,2025-10-15 10:00:00
        """)

        result = parse_status_log(str(log_file))

        assert len(result["clients"]) == 1
        assert result["clients"][0]["common_name"] == "client1"
```

### Mock Data

Create realistic mock data for testing:

- **status.log** samples with various scenarios
- **JSON fixtures** for session history and metrics
- **API responses** for geolocation services

## Documentation

### Code Documentation

- **Inline comments** - Explain complex logic
- **Docstrings** - Document all public functions and classes
- **Type hints** - Use Python type annotations

### User Documentation

When adding new features, update:

- **README.md** - Installation, features, API endpoints
- **translations/I18N.md** - Translation and internationalization guide

**Note:** CLAUDE.md is a developer-only file (excluded from git via .gitignore)

### Commit Messages

Follow these guidelines for commit messages:

```
<type>(<scope>): <subject>

<body>

<footer>
```

**Types:**
- `feat` - New feature
- `fix` - Bug fix
- `docs` - Documentation changes
- `style` - Code formatting (no logic change)
- `refactor` - Code restructuring (no behavior change)
- `test` - Adding or updating tests
- `chore` - Maintenance tasks

**Examples:**

```
feat(parser): add support for OpenVPN status version 4

Implement parser logic to handle version 4 format which includes
additional client connection metadata.

Closes #123
```

```
fix(routes): correct timezone handling in session history

Fixed issue where session durations were calculated incorrectly
for timezones with daylight saving time.

Fixes #456
```

## Submitting Changes

### Pull Request Process

1. **Update your fork**

   ```bash
   git fetch upstream
   git rebase upstream/main
   ```

2. **Make your changes**

   - Write code following style guidelines
   - Add or update tests
   - Update documentation

3. **Test your changes**

   ```bash
   pytest
   black .
   flake8
   ```

4. **Commit your changes**

   ```bash
   git add .
   git commit -m "feat(component): clear description of changes"
   ```

5. **Push to your fork**

   ```bash
   git push origin feature/your-feature-name
   ```

6. **Create Pull Request**

   - Go to your fork on GitHub
   - Click "New Pull Request"
   - Select your branch
   - Fill out the PR template

### Pull Request Guidelines

Your PR should:

- **Have a clear title** describing the change
- **Reference related issues** (e.g., "Fixes #123")
- **Include tests** for new functionality
- **Update documentation** if needed
- **Pass all CI checks** (tests, linting)
- **Be reasonably sized** - smaller PRs are easier to review

### Pull Request Template

```markdown
## Description
Brief description of changes

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## Testing
Describe how you tested your changes

## Checklist
- [ ] Code follows style guidelines
- [ ] Self-review completed
- [ ] Comments added for complex code
- [ ] Documentation updated
- [ ] Tests added/updated
- [ ] All tests pass
- [ ] No new warnings generated
```

### Code Review Process

After submitting a PR:

1. **Automated checks** will run (tests, linting)
2. **Maintainers will review** your code
3. **Address feedback** - Make requested changes
4. **Approval and merge** - Once approved, maintainers will merge

Be patient and responsive to feedback. Reviews help maintain code quality.

## Community

### Getting Help

- **GitHub Discussions** - Ask questions, share ideas
- **GitHub Issues** - Report bugs, request features
- **Documentation** - Check README.md, translations/I18N.md

### Recognition

Contributors will be recognized in:

- GitHub contributors list
- Release notes for significant contributions
- Project documentation

## License

By contributing to OpenVPN Monitor, you agree that your contributions will be licensed under the [MIT License](LICENSE).

---

Thank you for contributing to OpenVPN Monitor! Your efforts help make this project better for everyone.
