# WCAG Accessibility Scanner GitHub Action

Automatically scan HTML files for WCAG accessibility compliance using axe-core and Puppeteer. This action intelligently detects whether to scan the entire repository or only affected files based on the GitHub context.

## 🚀 Features

- **Smart Scanning**: Automatically detects PR vs. main branch pushes
- **PR Mode**: Fast scans of only changed files
- **Main Branch Mode**: Comprehensive scans of entire repository
- **WCAG 2.1 Compliance**: Uses axe-core for thorough accessibility testing
- **Multiple Output Formats**: Generates both HTML and JSON reports
- **Configurable**: Customize scan mode, output directory, and more

## 📋 Prerequisites

- Repository must contain HTML files
- GitHub Actions enabled on your repository

## 🔧 Usage

### Basic Usage

```yaml
- uses: mohammedfarhank/WCAG2.1-Scanner-github-action@main
  with:
    email: ${{ github.actor }}@company.com
    name: ${{ github.actor }}
```

### Advanced Usage

```yaml
- uses: mohammedfarhank/WCAG2.1-Scanner-github-action@main
  with:
    email: ${{ github.actor }}@company.com
    name: ${{ github.actor }}
    scan_mode: 'affected'  # 'auto', 'all', or 'affected'
    output_dir: './accessibility-reports'
```

## 📥 Inputs

| Input | Description | Required | Default |
|-------|-------------|----------|---------|
| `email` | Committer's email address | ✅ Yes | `${{ github.actor }}@localhost` |
| `name` | Committer's name | ✅ Yes | `${{ github.actor }}` |
| `scan_mode` | Scan mode: `auto`, `all`, or `affected` | ❌ No | `auto` |
| `output_dir` | Output directory for reports | ❌ No | `./reports` |

## 🔍 Scan Modes

### Auto Mode (Default)
- **Pull Requests**: Scans only affected/changed files (fast)
- **Direct pushes to main/master**: Scans entire repository (comprehensive)
- **Other contexts**: Scans entire repository

### All Mode
- Forces full repository scan regardless of context
- Use for comprehensive accessibility audits

### Affected Mode
- Forces scan of only changed files
- Use for fast PR checks

## 📊 Outputs

The action generates:
- **HTML Report**: Interactive report with violations, incomplete results, and test coverage
- **JSON Report**: Machine-readable data for further processing
- **Console Output**: Real-time scanning progress and results

## 📁 Report Structure

Reports are saved to the specified output directory:
```
reports/
├── report.html    # Interactive HTML report
└── report.json    # JSON data export
```

## 🎯 Example Workflows

### Pull Request Check

```yaml
name: Accessibility Check
on: [pull_request]

jobs:
  accessibility:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - uses: mohammedfarhank/WCAG2.1-Scanner-github-action@main
        with:
          email: ${{ github.actor }}@company.com
          name: ${{ github.actor }}
          scan_mode: 'affected'
      
      - uses: actions/upload-artifact@v4
        with:
          name: accessibility-report
          path: ./reports/
```

### Main Branch Audit

```yaml
name: Full Accessibility Audit
on:
  push:
    branches: [main, master]

jobs:
  accessibility:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - uses: mohammedfarhank/WCAG2.1-Scanner-github-action@main
        with:
          email: ${{ github.actor }}@company.com
          name: ${{ github.actor }}
          scan_mode: 'all'
      
      - uses: actions/upload-artifact@v4
        with:
          name: accessibility-report
          path: ./reports/
```

## 🔧 Configuration

### Excluded Directories

The scanner automatically excludes common build and dependency directories:
- `node_modules`, `dist`, `build`, `www`
- `.git`, `coverage`, `.angular`
- `ios`, `android`, `platforms`
- `.idea`, `.vscode`

### File Limits

- **HTML files**: Maximum 1000 files per scan
- **Timeout**: 120 seconds per file

## 🐛 Troubleshooting

### Common Issues

1. **No HTML files found**: Ensure your repository contains `.html` files
2. **Git diff failed**: The action will fall back to full repository scan
3. **Puppeteer timeout**: Large HTML files may take longer to process

### Debug Mode

Enable debug output by setting the `ACTIONS_STEP_DEBUG` secret to `true` in your repository.

## 📈 Performance

- **PR Mode**: Typically 2-5x faster than full scans
- **Main Branch Mode**: Comprehensive coverage for regression detection
- **Smart Fallbacks**: Automatically handles errors and edge cases

## 🤝 Contributing

Contributions are welcome! Please feel free to submit issues and pull requests.

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgments

- [axe-core](https://github.com/dequelabs/axe-core) for accessibility testing
- [Puppeteer](https://github.com/puppeteer/puppeteer) for HTML rendering
- [Rich](https://github.com/Textualize/rich) for beautiful console output 