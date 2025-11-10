# Contributing to Sound Monitor

Thank you for your interest in contributing to Sound Monitor! This document provides guidelines for contributing to the project.

## How to Contribute

### Reporting Bugs

1. Check if the bug has already been reported in GitHub Issues
2. If not, create a new issue with:
   - Clear, descriptive title
   - Steps to reproduce
   - Expected vs actual behavior
   - Your environment (OS, Python version, etc.)
   - Error messages or screenshots

### Suggesting Enhancements

1. Check existing issues and pull requests
2. Create a new issue describing:
   - The enhancement and its benefits
   - Potential implementation approach
   - Any drawbacks or limitations

### Pull Requests

1. Fork the repository
2. Create a new branch: `git checkout -b feature/your-feature-name`
3. Make your changes
4. Test thoroughly
5. Commit with clear messages
6. Push to your fork
7. Create a pull request

## Development Setup

1. **Clone the repository:**
   ```bash
   git clone https://github.com/DrewThomasson/sound-monitor.git
   cd sound-monitor
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   pip install psutil  # Optional
   ```

3. **Run tests:**
   ```bash
   python3 test_sound_monitor.py
   ```

4. **Run the application:**
   ```bash
   python3 sound_monitor.py
   ```

## Code Style

- Follow PEP 8 guidelines
- Use meaningful variable and function names
- Add docstrings to classes and functions
- Comment complex logic
- Keep functions focused and concise

## Testing

- Add tests for new features
- Ensure existing tests pass
- Test on multiple platforms if possible
- Test with and without audio hardware

## Areas for Contribution

### High Priority

- [ ] Cross-platform audio playback improvements
- [ ] Better error handling for device disconnections
- [ ] Automated testing with CI/CD
- [ ] Performance optimizations for long-running sessions
- [ ] Memory usage improvements

### Medium Priority

- [ ] Stereo recording support
- [ ] Multiple simultaneous device recording
- [ ] Advanced frequency analysis
- [ ] Noise source classification (ML-based)
- [ ] Cloud backup integration
- [ ] Mobile app companion

### Documentation

- [ ] Video tutorials
- [ ] More example workflows
- [ ] Translations
- [ ] API documentation
- [ ] Troubleshooting guides

### Low Priority

- [ ] Themes and customization
- [ ] Plugin system
- [ ] Web interface
- [ ] Remote monitoring
- [ ] Email notifications

## Code Organization

```
sound-monitor/
├── sound_monitor.py       # Main application
├── run.py                 # Launcher script
├── test_sound_monitor.py  # Test suite
├── example_demo.py        # Demo script
├── setup.py              # Installation script
├── requirements.txt      # Dependencies
├── README.md            # Main documentation
├── INSTALL.md          # Installation guide
├── QUICKSTART.md       # Quick reference
└── CONTRIBUTING.md     # This file
```

## Commit Message Guidelines

- Use present tense ("Add feature" not "Added feature")
- Use imperative mood ("Move cursor to..." not "Moves cursor to...")
- Limit first line to 72 characters
- Reference issues and pull requests

Examples:
```
Add stereo recording support

Implement frequency band analysis

Fix audio device selection on macOS (#123)

Update README with new features
```

## Review Process

1. All pull requests will be reviewed
2. Feedback will be provided constructively
3. Changes may be requested
4. Once approved, maintainers will merge

## License

By contributing, you agree that your contributions will be licensed under the MIT License.

## Questions?

- Open an issue for questions
- Tag with "question" label
- Be specific about what you need help with

## Recognition

Contributors will be:
- Listed in the project README
- Credited in release notes
- Acknowledged in the application

Thank you for helping make Sound Monitor better!
