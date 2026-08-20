# Wait for the two valid-set annotation runs to exit, then start the two
# verification runs. Four concurrent jobs were slowing every one of them and
# raising the odds of a queued-stall, so the verification pair is held back
# until the queue frees up.
#
# The trigger is process exit rather than a file count, so a run that dies part
# way through still releases the chain instead of blocking it forever.

$ErrorActionPreference = "Continue"
Set-Location "H:\Git\research\修論\llm-guideline-moderation-source"
$py  = "C:\Users\zhouh\anaconda3\python.exe"
$log = "logs\chain.log"

function Say($msg) {
    "$((Get-Date).ToString('MM-dd HH:mm:ss'))  $msg" | Tee-Object -FilePath $log -Append
}

Say "watcher started, waiting for the valid-set runs"

$deadline = (Get-Date).AddHours(6)
while ((Get-Date) -lt $deadline) {
    $running = Get-CimInstance Win32_Process -Filter "Name='python.exe'" |
        Where-Object { $_.CommandLine -like "*annotate_pubannotation_dir*" }
    if (-not $running) { break }
    Start-Sleep -Seconds 60
}

foreach ($n in 20, 30) {
    $d = "outputs\20260813_ncbi_gpt54-high_valid-M-dev$n"
    $c = if (Test-Path $d) { (Get-ChildItem $d -Filter *.json).Count } else { 0 }
    Say "valid-M-dev$n finished with $c / 100 documents"
}

$runs = @(
    @{ tag = "verifyA-noabs"
       name = "20260814_ncbi_gpt54-high_verified_dev10_noabstraction"
       extra = @("--no-abstraction") },
    @{ tag = "verifyC-abs"
       name = "20260814_ncbi_gpt54-high_verified_dev10_abstraction"
       extra = @() }
)

foreach ($r in $runs) {
    $a = @("-u", "reproduction/verified_refinement.py",
           "--dev-split", "reproduction/dev_splits/ncbi_disease_dev10.json",
           "--run-name", $r.name, "--max-attempts", "3",
           "--azure-model-key", "5_4", "--reasoning-effort", "high",
           "--max-output-tokens", "64000") + $r.extra
    Start-Process -FilePath $py -ArgumentList $a `
        -RedirectStandardOutput "logs\$($r.tag).log" `
        -RedirectStandardError  "logs\$($r.tag).err" -WindowStyle Hidden
    Say "started $($r.tag) -> $($r.name)"
    Start-Sleep -Seconds 5
}

Say "watcher done"
