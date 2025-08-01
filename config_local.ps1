# Mobile-Agent-E Local Configuration File
# Please fill in your real API keys

# ADB path configuration
$env:ADB_PATH = "C:\apps\adb\platform-tools\adb.exe"  # Windows default path
# $env:ADB_PATH = "adb"  # If adb is in PATH, use this

# Select backend model type
$env:BACKBONE_TYPE = "Qwen"  # Options: "OpenAI", "Gemini", "Claude", "Qwen", "GLM"

# === API Key Configuration (Required) ===

# Qwen related API keys (for perceptor)
$env:QWEN_API_KEY = "sk-a087535b2bc749f1aee28526cd151e7a"
$env:QWEN_REASONING_API_KEY = "sk-a087535b2bc749f1aee28526cd151e7a"
$env:DASHSCOPE_API_KEY = "sk-a087535b2bc749f1aee28526cd151e7a"

# GLM API key (Zhipu AI)
$env:GLM_API_KEY = "fbade139fe614df5b1581156edbf673e.Y0T8dlxYMEiCyfsQ"

# Display configuration status
Write-Host "=== Mobile-Agent-E Configuration Loaded ===" -ForegroundColor Green
Write-Host "ADB_PATH: $env:ADB_PATH"
Write-Host "BACKBONE_TYPE: $env:BACKBONE_TYPE"
