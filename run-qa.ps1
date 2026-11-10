<#
.SYNOPSIS
    QA runner for the AI child chatbot. No arguments = one FULL run of every scenario group and ONE HTML report.
.EXAMPLE
    .\run-qa.ps1 -Base https://test-env.example.invalid          # full run
    .\run-qa.ps1 -Task PRV -Base https://test-env.example.invalid # one scenario group (SAF, PRV, MEM, ONB)
    .\run-qa.ps1 -List                                           # coverage catalog
    .\run-qa.ps1 -ChatSelftest                                   # scenarios against a built-in fake server
    .\run-qa.ps1 -NoOpen                                         # do not open the browser
.NOTES
    Needs Python 3.12+ and the packages in requirements.txt. The base URL can also come from CHATQA_BASE_URL (config/local.env).
#>
param(
    [string[]]$Task,
    [string]$Base,
    [ValidateSet("both", "voice", "text")][string]$ChatMode = "both",
    [int]$ChatRuns = 0,
    [int]$ChatGap = 0,
    [switch]$List,
    [switch]$ChatSelftest,
    [switch]$NoOpen
)

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
$python = if (Test-Path ".\.venv\Scripts\python.exe") { ".\.venv\Scripts\python.exe" } else { "py" }

$a = @()
foreach ($t in $Task) { $a += @("--task", $t) }
if ($Base) { $a += @("--base", $Base) }
if ($List) { $a += "--list" }
if ($ChatRuns -gt 0) { $a += @("--chat-runs", $ChatRuns) }
if ($ChatGap -gt 0) { $a += @("--chat-gap", $ChatGap) }
if ($ChatSelftest) { $a += "--chat-selftest" }
$a += @("--chat-mode", $ChatMode)
if ($NoOpen) { $a += "--no-open" }
& $python run_qa.py @a
$code = $LASTEXITCODE
if ($code -eq 3) { Write-Host "STOPPED (exit code 3): the conversation with the assistant did not run. No report was written, nothing was saved." -ForegroundColor Red }
exit $code
