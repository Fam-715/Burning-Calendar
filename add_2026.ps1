# Burning Calendar - Zero Gravity, Zero Sleep. Written with AI assistance (declared on the project page).
# Usage: powershell -File add_2026.ps1 -Repo <this folder> -Downloads <folder with the FIRMS DL_FIRE_*.zip files and viirs-jpss1_MY_ID.csv> -OutFile <output .csv.gz>
# Adds January-October 2026 to data/harmonised_grid_monthly.csv.gz, following harmonise_firms.py:
# same cleaning, same 0.25-degree grid, and (as for every month from April 2018) hotspots = NOAA-20 count.
param([string]$Repo, [string]$Downloads, [string]$OutFile, [switch]$SelfTestOnly)
$ErrorActionPreference = "Stop"
Add-Type -AssemblyName System.IO.Compression.FileSystem
$inv = [Globalization.CultureInfo]::InvariantCulture
$LAST_MONTH = "2026-10"          # last complete month in the request files

function Get-Sensor([string]$sat) {
    switch ($sat.Trim().ToUpperInvariant()) {
        "TERRA" { "terra" } "T" { "terra" } "AQUA" { "aqua" } "A" { "aqua" }
        "N" { "snpp" } "SNPP" { "snpp" } "SUOMI NPP" { "snpp" }
        "N20" { "n20" } "NOAA-20" { "n20" } "1" { "n20" }
        default { "other" }
    }
}

# counts[key] = int[4] (terra, aqua, snpp, n20); key = ym|gy|gx|daynight
function Read-Csv($reader, $counts, $seen, [string]$ymFrom, [string]$ymTo, $stats) {
    $h = $reader.ReadLine().Split(",")
    $iLat = [Array]::IndexOf($h, "latitude"); $iLon = [Array]::IndexOf($h, "longitude")
    $iDate = [Array]::IndexOf($h, "acq_date"); $iSat = [Array]::IndexOf($h, "satellite")
    $iIns = [Array]::IndexOf($h, "instrument"); $iConf = [Array]::IndexOf($h, "confidence")
    $iDn = [Array]::IndexOf($h, "daynight"); $iType = [Array]::IndexOf($h, "type")
    while ($null -ne ($l = $reader.ReadLine())) {
        $f = $l.Split(",")
        $ym = $f[$iDate].Substring(0, 7)
        if ($ym -lt $ymFrom -or $ym -gt $ymTo) { continue }
        $stats.read++
        if ($iType -ge 0) {
            $t = $f[$iType].Trim()
            if ($t -ne "" -and [int][double]::Parse($t, $inv) -ne 0) { $stats.nonveg++; continue }
            $stats.typed++
        }
        $conf = $f[$iConf].Trim().ToLowerInvariant()
        if ($f[$iIns].Trim().ToUpperInvariant() -eq "MODIS") {
            $c = 0.0
            if (-not [double]::TryParse($conf, [Globalization.NumberStyles]::Float, $inv, [ref]$c)) { continue }
            if ($c -lt 30) { continue }
        } elseif ($conf -eq "l" -or $conf -eq "low") { continue }
        $s = Get-Sensor $f[$iSat]
        if ($s -eq "other") { continue }
        $dn = $f[$iDn].Trim()
        if (-not $seen.Add("$($f[$iLat])|$($f[$iLon])|$($f[$iDate])|$dn|$s")) { continue }   # drop_duplicates
        $gy = [int][math]::Floor([double]::Parse($f[$iLat], $inv) / 0.25)
        $gx = [int][math]::Floor([double]::Parse($f[$iLon], $inv) / 0.25)
        $key = "$ym|$gy|$gx|$dn"
        if (-not $counts.ContainsKey($key)) { $counts[$key] = [int[]]@(0, 0, 0, 0) }
        $idx = @{ terra = 0; aqua = 1; snpp = 2; n20 = 3 }[$s]
        $counts[$key][$idx]++
        $stats.kept++
    }
}

# ---- existing dataset: cell -> country, and December 2025 NOAA-20 total for the self-test ----
$gzPath = Join-Path $Repo "data\harmonised_grid_monthly.csv.gz"
$fs = [IO.File]::OpenRead($gzPath)
$sr = New-Object IO.StreamReader((New-Object IO.Compression.GZipStream($fs, [IO.Compression.CompressionMode]::Decompress)))
$header = $sr.ReadLine()
$old = New-Object System.Collections.Generic.List[string]
$cellCountry = @{}
$dec25 = 0.0; $dec25rows = 0
while ($null -ne ($l = $sr.ReadLine())) {
    if ($l.StartsWith("2026-")) { continue }                 # re-runs replace any earlier 2026 rows
    $old.Add($l)
    $f = $l.Split(",")
    $gy = [int][math]::Round([double]::Parse($f[3], $inv) / 0.25 - 0.5)
    $gx = [int][math]::Round([double]::Parse($f[4], $inv) / 0.25 - 0.5)
    $cellCountry["$gy|$gx"] = $f[5]
    if ($f[0] -eq "2025-12") { $dec25 += [double]::Parse($f[11], $inv); $dec25rows++ }
}
$sr.Close()
"existing rows kept: $($old.Count)   sample: $($old[$old.Count - 1])"

# ---- self-test: rebuild December 2025 NOAA-20 from the yearly file with this script's cleaning ----
$tc = @{}; $ts = New-Object System.Collections.Generic.HashSet[string]; $tstats = @{ read = 0; kept = 0; nonveg = 0; typed = 0 }
$r = New-Object IO.StreamReader((Join-Path $Downloads "viirs-jpss1_MY_ID.csv"))
Read-Csv $r $tc $ts "2025-12" "2025-12" $tstats
$r.Close()
$mine = 0; foreach ($v in $tc.Values) { $mine += $v[3] }
"SELF-TEST Dec 2025 NOAA-20: dataset says $dec25 in $dec25rows rows; this script counts $mine in $($tc.Count) rows"
if ($SelfTestOnly) { return }

# ---- 2026 request files (MODIS, S-NPP, NOAA-20; NOAA-21 is not used by the method) ----
$counts = @{}; $seen = New-Object System.Collections.Generic.HashSet[string]
$fileCountry = @{}       # request id -> country, for cells never seen before
$newCellCountry = @{}
foreach ($zip in Get-ChildItem (Join-Path $Downloads "DL_FIRE_*.zip") | Where-Object { $_.Name -notmatch "J2V" } | Sort-Object Name) {
    $country = if ($zip.Length -lt 1MB) { "Malaysia" } else { "Indonesia" }
    if ($zip.Name -match "M-C61_847983") { $country = "Malaysia" }
    $z = [IO.Compression.ZipFile]::OpenRead($zip.FullName)
    foreach ($e in $z.Entries | Where-Object { $_.Name -like "*.csv" }) {
        $stats = @{ read = 0; kept = 0; nonveg = 0; typed = 0 }
        $before = @{}; foreach ($k in $counts.Keys) { $before[$k] = $true }
        $rd = New-Object IO.StreamReader($e.Open())
        Read-Csv $rd $counts $seen "2026-01" $LAST_MONTH $stats
        $rd.Close()
        foreach ($k in $counts.Keys) {
            if (-not $before.ContainsKey($k)) { $p = $k.Split("|"); $ck = "$($p[1])|$($p[2])"; if (-not $newCellCountry.ContainsKey($ck)) { $newCellCountry[$ck] = $country } }
        }
        "  {0,-34} {1,-9} read {2,8:N0}  non-vegetation dropped {3,7:N0}  kept {4,8:N0}" -f $e.Name, $country, $stats.read, $stats.nonveg, $stats.kept
    }
    $z.Dispose()
}

# ---- rows in the dataset's format ----
$new = New-Object System.Collections.Generic.List[string]
$monthly = @{}; $unknownCells = 0
foreach ($k in ($counts.Keys | Sort-Object)) {
    $p = $k.Split("|"); $ym = $p[0]; $gy = [int]$p[1]; $gx = [int]$p[2]; $dn = $p[3]; $c = $counts[$k]
    $ck = "$gy|$gx"
    if ($cellCountry.ContainsKey($ck)) { $country = $cellCountry[$ck] } else { $country = $newCellCountry[$ck]; $unknownCells++ }
    $lat = (($gy + 0.5) * 0.25).ToString($inv); $lon = (($gx + 0.5) * 0.25).ToString($inv)
    $modis = $c[0] + $c[1]
    $new.Add("$ym,$($ym.Substring(0,4)),$([int]$ym.Substring(5)),$lat,$lon,$country,$dn,$($c[3]).0,VIIRS NOAA-20,$modis,$($c[2]),$($c[3])")
    if (-not $monthly.ContainsKey($ym)) { $monthly[$ym] = [int[]]@(0, 0, 0) }
    $monthly[$ym][0] += $modis; $monthly[$ym][1] += $c[2]; $monthly[$ym][2] += $c[3]
}
"2026 rows: $($new.Count)   rows in cells new to the dataset: $unknownCells"
"month     MODIS    S-NPP   NOAA-20 (= harmonised hotspots)"
foreach ($ym in ($monthly.Keys | Sort-Object)) { "{0}  {1,7:N0}  {2,7:N0}  {3,8:N0}" -f $ym, $monthly[$ym][0], $monthly[$ym][1], $monthly[$ym][2] }

# ---- write ----
$out = [IO.File]::Create($OutFile)
$gz = New-Object IO.Compression.GZipStream($out, [IO.Compression.CompressionLevel]::Optimal)
$sw = New-Object IO.StreamWriter($gz, (New-Object Text.UTF8Encoding $false))
$sw.NewLine = "`n"
$sw.WriteLine($header)
foreach ($l in $old) { $sw.WriteLine($l) }
foreach ($l in $new) { $sw.WriteLine($l) }
$sw.Close()
"written: $OutFile  ($([math]::Round((Get-Item $OutFile).Length / 1MB, 2)) MB, $($old.Count + $new.Count) rows)"
