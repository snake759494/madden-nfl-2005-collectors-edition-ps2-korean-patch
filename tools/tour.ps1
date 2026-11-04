param([string]$steps)
$emu = Join-Path $PSScriptRoot 'emu.ps1'
$shots = Join-Path $PSScriptRoot '..\shots'
foreach ($st in $steps.Split(' ')) {
  if ($st -eq '') { continue }
  if ($st.StartsWith('w:')) { Start-Sleep -Seconds ([double]$st.Substring(2)); continue }
  if ($st.StartsWith('s:')) { & $emu pshot (Join-Path $shots ($st.Substring(2) + '.png')) | Out-Null; continue }
  $n = 1; $k = $st
  if ($st -match '^(\w+)x(\d+)$') { $k = $Matches[1]; $n = [int]$Matches[2] }
  for ($i = 0; $i -lt $n; $i++) { & $emu kpost $k | Out-Null; Start-Sleep -Milliseconds 1500 }
}
