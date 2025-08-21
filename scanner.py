#!/usr/bin/env python3
"""
WCAG Accessibility Scanner with Web Interface - Using Puppeteer for HTML
"""
import os
import json
import time
import subprocess
import sys
import tempfile
import fnmatch
import argparse
from pathlib import Path
from typing import List, Dict, Any

def print_status(message, level="info"):
    """Print status messages with different formatting"""
    timestamp = time.strftime("%H:%M:%S")
    if level == "error":
        print(f"[{timestamp}] ❌ {message}")
    elif level == "warning":
        print(f"[{timestamp}] ⚠️ {message}")
    elif level == "success":
        print(f"[{timestamp}] ✅ {message}")
    elif level == "info":
        print(f"[{timestamp}] ℹ️ {message}")
    else:
        print(f"[{timestamp}] {message}")

def print_progress(current, total, description=""):
    """Print progress bar"""
    if total > 0:
        percentage = (current / total) * 100
        bar_length = 30
        filled_length = int(bar_length * current // total)
        bar = '█' * filled_length + '-' * (bar_length - filled_length)
        print(f"\r[{bar}] {percentage:.1f}% {description}", end='', flush=True)
        if current == total:
            print()  # New line when complete

class Config:
    REPO_PATH = os.environ.get('GITHUB_WORKSPACE', os.getcwd())
    OUTPUT_DIR = "./reports"
    SCAN_MODE = None  # Will be set by command line args: 'all', 'affected', or None for auto
    EXCLUDE_DIRS = [
        "node_modules", "dist", "build", "www", ".git", 
        "coverage", ".angular", "ios", "android", "platforms",
        "Pods", "DerivedData", ".idea", ".vscode"
    ]
    EXCLUDE_FILE_PATTERNS = ["*.d.ts", "*.spec.ts", "*.test.ts", "*.mock.ts", "*.data.ts"]
    FILE_LIMITS = {"html": 1000}
    TIMEOUT_PER_FILE = 120  # Increased timeout for Puppeteer

class AccessibilityScanner:
    def __init__(self):
        self.repo_path = Path(Config.REPO_PATH)
        self.output_dir = Path(Config.OUTPUT_DIR)
        self.output_dir.mkdir(exist_ok=True)
        
        # Get repository name for better display
        self.repo_name = self.get_repo_name()
    
    def get_repo_name(self) -> str:
        """Get a friendly repository name for display"""
        try:
            # Try to get repo name from git
            result = subprocess.run(['git', 'remote', 'get-url', 'origin'], 
                                  capture_output=True, text=True, timeout=10, cwd=str(self.repo_path))
            if result.returncode == 0 and result.stdout.strip():
                # Extract repo name from git URL
                url = result.stdout.strip()
                if 'github.com' in url:
                    # Extract owner/repo from https://github.com/owner/repo.git
                    parts = url.split('/')
                    if len(parts) >= 2:
                        return f"{parts[-2]}/{parts[-1].replace('.git', '')}"
                    else:
                        return "Unknown Repository"
                else:
                    return "Local Repository"
            else:
                # Fallback to directory name
                return self.repo_path.name if self.repo_path.name else "Repository"
        except Exception:
            # Final fallback
            return self.repo_path.name if self.repo_path.name else "Repository"
        
    def should_exclude_file(self, file_path: Path) -> bool:
        """Check if a file should be excluded based on patterns"""
        filename = file_path.name
        
        # Check against exclude patterns
        for pattern in Config.EXCLUDE_FILE_PATTERNS:
            if fnmatch.fnmatch(filename, pattern):
                return True
        
        # Check if file is in excluded directories
        exclude_dirs = set(Config.EXCLUDE_DIRS)
        for part in file_path.parts:
            if part in exclude_dirs:
                return True
        
        return False
        
    def find_files(self, pattern: str) -> List[Path]:
        """Find files matching pattern, excluding specified directories"""
        files = []
        exclude_dirs = set(Config.EXCLUDE_DIRS)
        
        print_status(f"Searching for {pattern} files...", "info")
        
        for root, dirs, filenames in os.walk(self.repo_path):
            # Skip excluded directories
            dirs[:] = [d for d in dirs if d not in exclude_dirs and not any(excl in root for excl in exclude_dirs)]
            
            for filename in filenames:
                if fnmatch.fnmatch(filename, f"*{pattern}"):
                    file_path = Path(root) / filename
                    
                    # Skip excluded files
                    if self.should_exclude_file(file_path):
                        continue
                    
                    files.append(file_path)
        
        print_status(f"Found {len(files)} {pattern} files.", "success")
        return files
    
    def get_affected_files(self, pattern: str) -> List[Path]:
        """Get only affected/changed files for PRs, or all files for direct pushes"""
        # Check command-line override first
        if Config.SCAN_MODE == 'all':
            print_status("🔍 Command-line override: scanning entire repository...", "info")
            return self.find_files(pattern)
        elif Config.SCAN_MODE == 'affected':
            print_status("🔍 Command-line override: scanning only affected files...", "info")
            return self.get_changed_files(pattern)
        
        # Check if we're in a GitHub Actions environment
        github_event = os.environ.get('GITHUB_EVENT_NAME', '')
        github_base_ref = os.environ.get('GITHUB_BASE_REF', '')
        github_head_ref = os.environ.get('GITHUB_HEAD_REF', '')
        
        print_status(f"GitHub context: Event={github_event}, Base={github_base_ref}, Head={github_head_ref}", "info")
        
        # If it's a PR, scan only affected files
        if github_event == 'pull_request':
            print_status("🔍 Pull Request detected - scanning only affected files...", "info")
            return self.get_changed_files(pattern)
        
        # If it's a direct push to main/master, scan everything
        elif github_event == 'push' and github_base_ref in ['main', 'master']:
            print_status("🔍 Direct push to main/master detected - scanning entire repository...", "info")
            return self.find_files(pattern)
        
        # Default: scan everything (fallback for local runs or other contexts)
        else:
            print_status("🔍 Default mode - scanning entire repository...", "info")
            return self.find_files(pattern)
    
    def get_changed_files(self, pattern: str) -> List[Path]:
        """Get only files that have changed in the current PR"""
        try:
            # Get the base branch (usually main or master)
            base_branch = os.environ.get('GITHUB_BASE_REF', 'main')
            
            # Get changed files using git diff
            result = subprocess.run([
                'git', 'diff', '--name-only', f'origin/{base_branch}...HEAD'
            ], capture_output=True, text=True, timeout=30, cwd=str(self.repo_path))
            
            if result.returncode != 0:
                print_status(f"⚠️ Git diff failed, falling back to full scan: {result.stderr}", "warning")
                return self.find_files(pattern)
            
            changed_files = result.stdout.strip().split('\n') if result.stdout.strip() else []
            print_status(f"Git diff found {len(changed_files)} changed files", "info")
            
            # Filter for files matching the pattern
            matching_files = []
            for file_path in changed_files:
                if file_path and fnmatch.fnmatch(file_path, f"*{pattern}"):
                    full_path = self.repo_path / file_path
                    if full_path.exists() and not self.should_exclude_file(full_path):
                        matching_files.append(full_path)
            
            print_status(f"Found {len(matching_files)} changed {pattern} files.", "success")
            return matching_files
            
        except Exception as e:
            print_status(f"⚠️ Error getting changed files: {e}, falling back to full scan", "warning")
            return self.find_files(pattern)
    
    def scan_html_with_puppeteer_axe(self, html_file: Path) -> str:
        """Scan HTML file using Puppeteer and axe-core"""
        try:
            # Create a Node.js script to run axe with Puppeteer
            script_content = f"""
            const fs = require('fs');
            const puppeteer = require('puppeteer');
            
            async function runAxe() {{
                const browser = await puppeteer.launch({{ 
                    headless: 'new',
                    executablePath: process.env.PUPPETEER_EXECUTABLE_PATH || undefined,
                    args: ['--no-sandbox', '--disable-setuid-sandbox', '--disable-web-security']
                }});
                const page = await browser.newPage();
                
                try {{
                    await page.setDefaultNavigationTimeout(60000);
                    const htmlContent = fs.readFileSync('{html_file.absolute()}', 'utf8');
                    await page.setContent(htmlContent, {{
                        waitUntil: 'networkidle0',
                        timeout: 60000
                    }});
                    
                    // Use globally installed axe-core
                    const axeCorePath = require.resolve('axe-core');
                    const axeScript = fs.readFileSync(axeCorePath, 'utf8');
                    await page.evaluate(axeScript);
                    
                    const results = await page.evaluate(async () => {{
                        return await axe.run();
                    }});
                    console.log(JSON.stringify(results));
                    await browser.close();
                    process.exit(0);
                }} catch (error) {{
                    console.error(JSON.stringify({{ error: error.message, stack: error.stack }}));
                    await browser.close();
                    process.exit(1);
                }}
            }}
            
            runAxe().catch(error => {{
                console.error(JSON.stringify({{ error: error.message, stack: error.stack }}));
                process.exit(1);
            }});
            """
            
            # Write temporary script
            temp_dir = os.path.abspath(str(self.repo_path))
            with tempfile.NamedTemporaryFile(mode='w', suffix='.js', delete=False, dir=temp_dir) as script_file:
                script_file.write(script_content)
                script_path = script_file.name
            
            # Run the script
            result = subprocess.run([
                'node', script_path
            ], capture_output=True, text=True, timeout=Config.TIMEOUT_PER_FILE, cwd=str(self.repo_path))
            
            # Clean up script
            os.unlink(script_path)
            
            print_status(f"Puppeteer exit code for {html_file.name}: {result.returncode}", "info")
            print_status(f"Puppeteer STDOUT: {result.stdout[:200]}...", "info")
            print_status(f"Puppeteer STDERR: {result.stderr[:200]}...", "info")
            
            if result.returncode == 0 and result.stdout.strip():
                try:
                    return json.loads(result.stdout)
                except json.JSONDecodeError:
                    return {"error": f"Invalid JSON output for {html_file.name}: {result.stdout}"}
            else:
                error_msg = result.stderr if result.stderr else result.stdout
                try:
                    error_data = json.loads(error_msg)
                    return {"error": error_data.get('error', error_msg)}
                except:
                    return {"error": f"Puppeteer error for {html_file.name}: {error_msg}"}
                
        except subprocess.TimeoutExpired:
            return {"error": f"Timeout after {Config.TIMEOUT_PER_FILE} seconds for {html_file.name}"}
        except Exception as e:
            return {"error": f"Exception for {html_file.name}: {str(e)}"}
    
    def scan_html_with_alternative_method(self, html_file: Path) -> Dict[str, Any]:
        """Alternative method using direct HTML content analysis"""
        try:
            # Read HTML content
            content = html_file.read_text(encoding='utf-8', errors='ignore')
            
            # Simple accessibility checks (fallback method)
            violations = []
            
            # Check for missing alt text
            img_tags = content.split('<img')
            for i, img_tag in enumerate(img_tags[1:]):  # Skip first split part
                if ' alt=' not in img_tag and ' alt =' not in img_tag:
                    violations.append({
                        "id": "image-alt",
                        "impact": "critical",
                        "help": "Images must have alternate text",
                        "helpUrl": "https://dequeuniversity.com/rules/axe/4.7/image-alt",
                        "nodes": [{
                            "html": f"<img{img_tag.split('>')[0]}>",
                            "target": [f"img:nth-of-type({i+1})"]
                        }]
                    })
            
            # Check for missing form labels
            form_elements = ['<input', '<select', '<textarea']
            for element in form_elements:
                if element in content:
                    element_tags = content.split(element)
                    for i, tag in enumerate(element_tags[1:]):
                        if (' id=' not in tag or ' for=' not in content) and ' aria-label=' not in tag:
                            violations.append({
                                "id": "label",
                                "impact": "serious",
                                "help": "Form elements must have labels",
                                "helpUrl": "https://dequeuniversity.com/rules/axe/4.7/label",
                                "nodes": [{
                                    "html": f"{element}{tag.split('>')[0]}>",
                                    "target": [f"{element[1:]}:nth-of-type({i+1})"]
                                }]
                            })
            
            # Check for missing lang attribute
            if '<html' in content and ' lang=' not in content and ' lang =' not in content:
                violations.append({
                    "id": "html-has-lang",
                    "impact": "serious",
                    "help": "<html> element must have a lang attribute",
                    "helpUrl": "https://dequeuniversity.com/rules/axe/4.7/html-has-lang",
                    "nodes": [{
                        "html": "<html>",
                        "target": ["html"]
                    }]
                })
            
            # Check for missing document title
            if '<title>' not in content:
                violations.append({
                    "id": "document-title",
                    "impact": "serious",
                    "help": "Documents must have a title element",
                    "helpUrl": "https://dequeuniversity.com/rules/axe/4.7/document-title",
                    "nodes": [{
                        "html": "<head>",
                        "target": ["head"]
                    }]
                })
            
            return {
                "violations": violations,
                "passes": [],
                "incomplete": [],
                "inapplicable": [],
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                "url": f"file://{html_file.absolute()}"
            }
            
        except Exception as e:
            return {"error": f"Exception for {html_file.name}: {str(e)}"}
    
    def scan_html_file(self, html_file: Path) -> Dict[str, Any]:
        """Main HTML scanning method using Puppeteer"""
        print_status(f"Scanning: {html_file.name}", "info")
        
        # Try Puppeteer method
        result = self.scan_html_with_puppeteer_axe(html_file)
        
        # If Puppeteer fails, use fallback
        if "error" in result:
            print_status(f"⚠️ Puppeteer failed for {html_file.name}, using fallback method", "warning")
            result = self.scan_html_with_alternative_method(html_file)
        
        return result
    
    def generate_html_report(self, results: Dict[str, Any]):
        """Generate interactive HTML report with pagination, violations, and incomplete results"""
        import html
        print_status("🔍 Generating HTML report...", "info")
        print_status(f"Results keys: {list(results.keys())}", "info")  # Debug: Print file paths
        print_status(f"Total results: {len(results)}", "info")  # Debug: Print total files
        
        html_template = """
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>WCAG Accessibility Report</title>
            <style>
                body { font-family: Arial, sans-serif; margin: 40px; background: #f5f5f5; }
                .container { max-width: 1200px; margin: 0 auto; background: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
                .header { background: #2c3e50; color: white; padding: 20px; border-radius: 5px; margin-bottom: 30px; }
                .summary-card { background: #ecf0f1; padding: 20px; border-radius: 5px; margin-bottom: 20px; }
                .violation { background: #ffe6e6; border-left: 4px solid #e74c3c; padding: 15px; margin: 10px 0; border-radius: 3px; }
                .incomplete { background: #fff3cd; border-left: 4px solid #ffc107; padding: 15px; margin: 10px 0; border-radius: 3px; }
                .success { background: #d4edda; border-left: 4px solid #28a745; padding: 15px; margin: 10px 0; border-radius: 3px; }
                .file-section { margin: 20px 0; padding: 15px; background: #f8f9fa; border-radius: 5px; }
                .toggle { cursor: pointer; color: #3498db; }
                .hidden { display: none; }
                .impact-critical { border-left-color: #e74c3c !important; }
                .impact-serious { border-left-color: #e67e22 !important; }
                .impact-moderate { border-left-color: #f39c12 !important; }
                .impact-minor { border-left-color: #f1c40f !important; }
                .error { background: #f8d7da; border-left: 4px solid #dc3545; padding: 15px; margin: 10px 0; border-radius: 3px; }
                .code-snippet { background: #f1f1f1; padding: 10px; border-radius: 3px; font-family: monospace; overflow-x: auto; white-space: pre-wrap; }
                .pagination { margin: 20px 0; text-align: center; }
                .pagination button { padding: 10px 20px; margin: 0 5px; cursor: pointer; }
                .pagination button:disabled { cursor: not-allowed; opacity: 0.5; }
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🔍 WCAG Accessibility Report</h1>
                    <p>Generated on {{timestamp}}</p>
                </div>
                
                <div class="summary-card">
                    <h2>📊 Summary</h2>
                    <p><strong>Total files scanned:</strong> {{total_files}}</p>
                    <p><strong>Total violations found:</strong> {{total_violations}}</p>
                    <p><strong>Total incomplete results:</strong> {{total_incomplete}}</p>
                    <p><strong>Files with errors:</strong> {{error_files}}</p>
                    <p><strong>Repository:</strong> {{repo_path}}</p>
                </div>
                
                <div class="summary-card">
                    <h2 class="toggle" onclick="toggleSection('tests-executed')">
                        🧪 Tests Executed <small>(Click to expand)</small>
                    </h2>
                    <div id="tests-executed" class="hidden">
                        <h3>Actual Tests Run by axe-core:</h3>
                        {{tests_executed_section}}
                        <p><em>Note: These are the actual axe-core test IDs that were run during the scan. Each ID represents a specific WCAG accessibility rule.</em></p>
                    </div>
                </div>
                
                <div class="pagination">
                    <button onclick="prevPage()" id="prevBtn">Previous</button>
                    <span id="pageInfo"></span>
                    <button onclick="nextPage()" id="nextBtn">Next</button>
                </div>
                
                <h2>📋 Detailed Results</h2>
                <div id="results">{{results}}</div>
            </div>
            
            <script>
                try {
                    const resultsDiv = document.getElementById('results');
                    const fileSections = Array.from(resultsDiv.getElementsByClassName('file-section'));
                    const filesPerPage = 10;
                    let currentPage = 0;
                    
                    function showPage(page) {
                        fileSections.forEach((section, index) => {
                            section.style.display = (index >= page * filesPerPage && index < (page + 1) * filesPerPage) ? 'block' : 'none';
                        });
                        document.getElementById('pageInfo').textContent = `Page ${page + 1} of ${Math.ceil(fileSections.length / filesPerPage)}`;
                        document.getElementById('prevBtn').disabled = page === 0;
                        document.getElementById('nextBtn').disabled = page === Math.ceil(fileSections.length / filesPerPage) - 1;
                    }
                    
                    function prevPage() {
                        if (currentPage > 0) {
                            currentPage--;
                            showPage(currentPage);
                        }
                    }
                    
                    function nextPage() {
                        if (currentPage < Math.ceil(fileSections.length / filesPerPage) - 1) {
                            currentPage++;
                            showPage(currentPage);
                        }
                    }
                    
                    function toggleSection(id) {
                        const element = document.getElementById(id);
                        element.classList.toggle('hidden');
                    }
                    
                    showPage(0); // Initialize first page
                } catch (e) {
                    alert('Error rendering report: ' + e.message);
                    console.error(e);
                }
            </script>
        </body>
        </html>
        """
        
        total_violations = 0
        total_incomplete = 0
        total_files = len(results)
        error_files = 0
        results_html = []
        
        # Collect actual tests that were run
        tests_executed = set()
        tests_passed = set()
        tests_inapplicable = set()
        
        # Process each file in results
        for file_path, file_results in sorted(results.items()):  # Sort for consistent order
            print_status(f"Processing file: {file_path}", "info")  # Debug: Log each file
            file_id = file_path.replace('/', '_').replace('.', '_').replace(' ', '_')
            
            if isinstance(file_results, dict) and 'error' in file_results:
                error_files += 1
                results_html.append(f'''
                <div class="file-section">
                    <h3 class="toggle" onclick="toggleSection('{file_id}')">
                        ❌ {html.escape(file_path)} <small>(Error during scan)</small>
                    </h3>
                    <div id="{file_id}" class="hidden">
                        <div class="error">
                            <p><strong>Error:</strong> {html.escape(str(file_results.get('error', 'Unknown error')))}</p>
                            {f'<p><strong>Details:</strong> {html.escape(str(file_results.get("stderr", "")))}</p>' if file_results.get("stderr") else ''}
                        </div>
                    </div>
                </div>
                ''')
            else:
                # Handle Puppeteer output (.html)
                violations = []
                incomplete = []
                passes = []
                inapplicable = []
                
                if isinstance(file_results, dict) and 'violations' in file_results:
                    # Puppeteer output
                    violations = file_results.get('violations', [])
                    incomplete = file_results.get('incomplete', [])
                    passes = file_results.get('passes', [])
                    inapplicable = file_results.get('inapplicable', [])
                    
                    # Collect test IDs from all result types
                    for violation in violations:
                        tests_executed.add(violation.get('id', 'unknown'))
                    for inc in incomplete:
                        tests_executed.add(inc.get('id', 'unknown'))
                    for pass_test in passes:
                        tests_passed.add(pass_test.get('id', 'unknown'))
                    for inapp in inapplicable:
                        tests_inapplicable.add(inapp.get('id', 'unknown'))
                
                total_violations += len(violations)
                total_incomplete += len(incomplete)
                
                print_status(f"Violations for {file_path}: {len(violations)}", "info")  # Debug: Log violations
                print_status(f"Incomplete results for {file_path}: {len(incomplete)}", "info")  # Debug: Log incomplete
                
                if violations or incomplete:
                    results_html.append(f'''
                    <div class="file-section">
                        <h3 class="toggle" onclick="toggleSection('{file_id}')">
                            📄 {html.escape(file_path)} <small>({len(violations)} violations, {len(incomplete)} incomplete)</small>
                        </h3>
                        <div id="{file_id}" class="hidden">
                    ''')
                    
                    # Render violations
                    for i, violation in enumerate(violations):
                        impact = violation.get('impact', 'unknown')
                        help_text = violation.get('help', 'No description')
                        help_url = violation.get('helpUrl', '#')
                        html_snippet = violation.get('nodes', [{}])[0].get('html', '')
                        failure_summary = violation.get('nodes', [{}])[0].get('failureSummary', '')
                        
                        # Replace problematic tags in html_snippet
                        html_snippet = html_snippet.replace('<title>', '&lt;title&gt;').replace('</title>', '&lt;/title&gt;')
                        failure_summary = html.escape(failure_summary.replace('<title>', '&lt;title&gt;').replace('</title>', '&lt;/title&gt;'))
                        
                        results_html.append(f'''
                            <div class="violation impact-{html.escape(impact)}">
                                <h4>Violation #{i+1}: {html.escape(violation.get('id', 'Unknown'))} <small>(Impact: {html.escape(impact)})</small></h4>
                                <p><strong>Description:</strong> {html.escape(help_text)}</p>
                                <p><strong>Help:</strong> <a href="{html.escape(help_url)}" target="_blank">{html.escape(help_url)}</a></p>
                                {f'<div class="code-snippet"><strong>Code:</strong> {html.escape(html_snippet)}</div>' if html_snippet else ''}
                                {f'<p><strong>Failure Summary:</strong> {failure_summary}</p>' if failure_summary else ''}
                            </div>
                        ''')
                    
                    # Render incomplete results
                    for i, inc in enumerate(incomplete):
                        impact = inc.get('impact', 'unknown')
                        help_text = inc.get('help', 'No description')
                        help_url = inc.get('helpUrl', '#')
                        html_snippet = inc.get('nodes', [{}])[0].get('html', '')
                        
                        html_snippet = html_snippet.replace('<title>', '&lt;title&gt;').replace('</title>', '&lt;/title&gt;')
                        
                        results_html.append(f'''
                            <div class="incomplete impact-{html.escape(impact)}">
                                <h4>Incomplete #{i+1}: {html.escape(inc.get('id', 'Unknown'))} <small>(Impact: {html.escape(impact)})</small></h4>
                                <p><strong>Description:</strong> {html.escape(help_text)}</p>
                                <p><strong>Help:</strong> <a href="{html.escape(help_url)}" target="_blank">{html.escape(help_url)}</a></p>
                                {f'<div class="code-snippet"><strong>Code:</strong> {html.escape(html_snippet)}</div>' if html_snippet else ''}
                            </div>
                        ''')
                    
                    results_html.append('</div></div>')
                else:
                    results_html.append(f'''
                    <div class="file-section">
                        <h3 class="toggle" onclick="toggleSection('{file_id}')">
                            ✅ {html.escape(file_path)} <small>(No violations or incomplete results)</small>
                        </h3>
                        <div id="{file_id}" class="hidden success">
                            <p>No accessibility issues found in this file.</p>
                        </div>
                    </div>
                    ''')
        
        # Generate tests executed section content
        if tests_executed or tests_passed or tests_inapplicable:
            tests_executed_section = f"""
                <div style="margin-bottom: 20px;">
                    <h4>🔴 Tests with Issues Found:</h4>
                    {f'<p><strong>Total violations/incomplete:</strong> {len(tests_executed)}</p><ul>{chr(10).join([f"<li><strong>{test_id}</strong></li>" for test_id in sorted(tests_executed)])}</ul>' if tests_executed else '<p><em>No violations or incomplete results found! 🎉</em></p>'}
                </div>
                
                <div style="margin-bottom: 20px;">
                    <h4>🟢 Tests That Passed:</h4>
                    {f'<p><strong>Total passed tests:</strong> {len(tests_passed)}</p><ul>{chr(10).join([f"<li><strong>{test_id}</strong></li>" for test_id in sorted(tests_passed)])}</ul>' if tests_passed else '<p><em>No tests passed (possibly due to errors or limited content)</em></p>'}
                </div>
                
                <div style="margin-bottom: 20px;">
                    <h4>⚪ Tests Not Applicable:</h4>
                    {f'<p><strong>Total inapplicable tests:</strong> {len(tests_inapplicable)}</p><ul>{chr(10).join([f"<li><strong>{test_id}</strong></li>" for test_id in sorted(tests_inapplicable)])}</ul>' if tests_inapplicable else '<p><em>All tests were applicable to your content</em></p>'}
                </div>
                
                <div style="background: #f8f9fa; padding: 15px; border-radius: 5px; margin-top: 20px;">
                    <p><strong>📊 Total Testing Coverage:</strong></p>
                    <ul>
                        <li><strong>Total unique tests run:</strong> {len(tests_executed | tests_passed | tests_inapplicable)}</li>
                        <li><strong>Tests with issues:</strong> {len(tests_executed)}</li>
                        <li><strong>Tests passed:</strong> {len(tests_passed)}</li>
                        <li><strong>Tests not applicable:</strong> {len(tests_inapplicable)}</li>
                    </ul>
                </div>
            """
        else:
            # Check if no HTML files were found
            if total_files == 0:
                tests_executed_section = f"""
                    <div style="background: #fff3cd; padding: 15px; border-radius: 5px; border-left: 4px solid #ffc107;">
                        <h4>⚠️ No Tests Executed</h4>
                        <p><strong>Reason:</strong> No HTML files were found in the repository <strong>{self.repo_name}</strong>.</p>
                        <p><strong>What this means:</strong></p>
                        <ul>
                            <li>This repository doesn't contain any <code>.html</code> files</li>
                            <li>HTML files might be in excluded directories (like <code>dist</code>, <code>build</code>, etc.)</li>
                            <li>HTML files might have different extensions (like <code>.htm</code>)</li>
                        </ul>
                        <p><strong>To run accessibility tests:</strong></p>
                        <ul>
                            <li>Ensure your repository contains <code>.html</code> files</li>
                            <li>Check that HTML files are not in excluded directories</li>
                            <li>Consider adding HTML files to test accessibility compliance</li>
                        </ul>
                    </div>
                """
            else:
                tests_executed_section = '<p><em>No tests were executed (possibly due to errors or empty results)</em></p>'
        
        # Replace placeholders
        html_content = html_template \
            .replace('{{timestamp}}', time.strftime('%Y-%m-%d %H:%M:%S')) \
            .replace('{{total_files}}', str(total_files)) \
            .replace('{{total_violations}}', str(total_violations)) \
            .replace('{{total_incomplete}}', str(total_incomplete)) \
            .replace('{{error_files}}', str(error_files)) \
            .replace('{{repo_path}}', str(self.repo_name)) \
            .replace('{{tests_executed_section}}', tests_executed_section) \
            .replace('{{results}}', '\n'.join(results_html) if results_html else '<div class="success">🎉 No accessibility issues found!</div>')
        
        # Validate HTML size
        html_lines = len(html_content.splitlines())
        print_status(f"Generated HTML lines: {html_lines}", "info")
        if html_lines < 100 or total_files != len(results_html):
            print_status(f"⚠️ Warning: HTML may be truncated. Expected {total_files} file sections, found {len(results_html)}", "warning")
        
        # Save HTML report
        html_report_path = self.output_dir / "report.html"
        with open(html_report_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        print_status(f"✓ HTML report generated: {html_report_path} (approx. {html_lines} lines)", "success")
        return html_report_path
    
    def generate_json_report(self, results: Dict[str, Any]):
        """Generate JSON report"""
        report_path = self.output_dir / "report.json"
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        return report_path
    
    def run_scan(self):
        """Main scanning method"""
        print_status("🚀 Starting WCAG Accessibility Scan", "success")
        print_status(f"Repository: {self.repo_path}", "info")
        
        # Find files using intelligent detection
        html_files = self.get_affected_files('.html')[:Config.FILE_LIMITS["html"]]
        
        print_status(f"Found: {len(html_files)} .html files to scan", "success")
        
        results = {}
        
        # Scan HTML files
        if html_files:
            print_status("📄 Scanning .html files with Puppeteer...", "info")
            
            for i, html_file in enumerate(html_files):
                print_progress(i + 1, len(html_files), f"Scanning {html_file.name}")
                results[str(html_file.relative_to(self.repo_path))] = self.scan_html_file(html_file)
            
            print()  # New line after progress bar
        else:
            print_status(f"⚠️ No HTML files found to scan in {self.repo_name}. No tests will be executed.", "warning")
        
        # Generate reports
        print_status("📊 Generating reports...", "info")
        json_report = self.generate_json_report(results)
        html_report = self.generate_html_report(results)
        
        print_status(f"✓ JSON report: {json_report}", "success")
        print_status(f"✓ HTML report: {html_report}", "success")
        print_status("✅ Scan completed!", "success")
        
        return html_report

def main():
    """Main function"""
    try:
        # Parse command-line arguments
        parser = argparse.ArgumentParser(description='WCAG Accessibility Scanner')
        parser.add_argument('--mode', choices=['auto', 'all', 'affected'], 
                          default='auto', help='Scan mode: auto (default), all (entire repo), or affected (changed files only)')
        parser.add_argument('--repo-path', help='Repository path (defaults to GITHUB_WORKSPACE or current directory)')
        parser.add_argument('--output-dir', default='./reports', help='Output directory for reports (default: ./reports)')
        
        args = parser.parse_args()
        
        # Set configuration based on arguments
        if args.mode != 'auto':
            Config.SCAN_MODE = args.mode
        if args.repo_path:
            Config.REPO_PATH = args.repo_path
        if args.output_dir:
            Config.OUTPUT_DIR = args.output_dir
        
        scanner = AccessibilityScanner()
        
        print_status("🔧 Configuration:", "info")
        print_status(f"  Scan Mode: {args.mode}", "info")
        print_status(f"  Repository: {scanner.repo_name}", "info")
        print_status(f"  Output: {Config.OUTPUT_DIR}", "info")
        print("")
        
        html_report = scanner.run_scan()
        
        print_status(f"✅ Scan completed! Report saved to: {html_report}", "success")
        print_status("📊 The HTML report can be downloaded as an artifact from the GitHub Actions run.", "info")
        
    except KeyboardInterrupt:
        print_status("⏹️ Scan interrupted by user", "warning")
    except Exception as e:
        print_status(f"❌ Error: {e}", "error")
        import traceback
        print_status(f"{traceback.format_exc()}", "info")
        sys.exit(1)

if __name__ == "__main__":
    main()