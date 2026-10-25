# Local voice-over: Windows built-in speech (System.Speech), one WAV per line. No network, no key.
param([string]$Dir = $PSScriptRoot)
Add-Type -AssemblyName System.Speech
$s = New-Object System.Speech.Synthesis.SpeechSynthesizer
Write-Output ("voice: " + $s.Voice.Name)
$s.Rate = -1
$i = 1
foreach ($line in Get-Content (Join-Path $Dir "lines.txt")) {
  if (-not $line.Trim()) { continue }
  $s.SetOutputToWaveFile((Join-Path $Dir ("line-{0:00}.wav" -f $i)))
  $s.Speak($line)
  $i++
}
$s.Dispose()
