# Start the third abstraction run once a slot frees up.
#
# Two concurrent runs have been reliable; four were not, and three are untested,
# so the third run waits rather than competing. The trigger is "fewer than two
# moderation processes alive", so a run that dies part way through releases the
# slot instead of blocking it forever.

$ErrorActionPreference = "Continue"
Set-Location "H:\Git\research\修論\llm-guideline-moderation-source"
$py  = "C:\Users\zhouh\anaconda3\python.exe"
$log = "logs\chain-abs3.log"

function Say($msg) {
    "$((Get-Date).ToString('MM-dd HH:mm:ss'))  $msg" | Tee-Object -FilePath $log -Append
}

Say "watcher started, waiting for a free slot"

$deadline = (Get-Date).AddHours(8)
while ((Get-Date) -lt $deadline) {
    $running = @(Get-CimInstance Win32_Process -Filter "Name='python.exe'" |
        Where-Object { $_.CommandLine -like "*run_iterative_refinement*" -or
                       $_.CommandLine -like "*ablation_abstraction_only*" })
    if ($running.Count -lt 2) { break }
    Start-Sleep -Seconds 60
}

Start-Process -FilePath $py -ArgumentList @(
    "-u", "reproduction/ablation_abstraction_only.py",
    "--dev-split", "reproduction/dev_splits/ncbi_disease_dev10.json",
    "--run-name", "20260814_ncbi_gpt54-high_moderation-abstraction_run3",
    "--azure-model-key", "5_4", "--reasoning-effort", "high",
    "--max-output-tokens", "64000"
) -RedirectStandardOutput "logs\abs-run3.log" -RedirectStandardError "logs\abs-run3.err" -WindowStyle Hidden

Say "started abstraction run3"
