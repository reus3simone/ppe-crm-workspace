Write-Host "正在启动 PPE客户开发工作区 ..."
$streamlit = Join-Path $PSScriptRoot "venv\Scripts\streamlit.exe"
$app = Join-Path $PSScriptRoot "app.py"
& $streamlit run $app --server.port 8501
Read-Host "按 Enter 键退出"
