@echo off
setlocal enabledelayedexpansion

:: === CONFIGURATION ===
set "CHUNK_SIZE=250G"

:: === PROCESS EACH FILE PASSED AS ARGUMENT ===
for %%F in (%*) do (
    echo Processing: %%~nxF

    set "FILENAME=%%~nF"
    set "EXTENSION=%%~xF"

    :: Get duration of the input video in seconds
    for /f "tokens=1 delims=." %%D in ('ffprobe -v error -show_entries format^=duration -of default^=noprint_wrappers^=1:nokey^=1 "%%F"') do (
        set /a DURATION=%%D
    )

    :: Estimate bitrate in bits per second (bps)
    for /f "tokens=1" %%S in ('ffprobe -v error -select_streams v:0 -show_entries stream^=bit_rate -of default^=noprint_wrappers^=1:nokey^=1 "%%F"') do (
        set /a BITRATE=%%S
    )

    if not defined BITRATE (
        echo Could not get bitrate, using fallback method...
        :: fallback: estimate based on file size
        for %%A in ("%%F") do set /a BITRATE=%%~zA*8/!DURATION!
    )

    :: Calculate max duration per 250GB chunk (in seconds)
    set /a MAX_DURATION=!CHUNK_SIZE:~0,-1!*1024*1024*1024*8/!BITRATE!

    set /a START=0
    set /a INDEX=1

    :loop
    if !START! GEQ !DURATION! goto :eof

    echo Splitting chunk !INDEX! starting at !START!s for !MAX_DURATION!s
    ffmpeg -y -hide_banner -loglevel error -ss !START! -i "%%F" -t !MAX_DURATION! -c copy "!FILENAME!_Part-!INDEX!!EXTENSION!"

    set /a START+=MAX_DURATION
    set /a INDEX+=1
    goto loop
)
