@echo off
@setlocal

:Variables
set start=%time%

:: make the entry point for the King Phisher client build
copy king_phisher\client\__main__.py .\KingPhisher
if %ERRORLEVEL% NEQ 0 (
	echo Failed to copy client entry point
	echo Error level: %ERRORLEVEL%
	exit /b %ERRORLEVEL%
)

:: perform the build
python tools\development\cx_freeze.py build
if %ERRORLEVEL% NEQ 0 (
	echo Failed to build the King Phisher exe
	echo Error level: %ERRORLEVEL%
	exit /b %ERRORLEVEL%
)
python tools\development\cx_freeze.py bdist_msi
if %ERRORLEVEL% NEQ 0 (
	echo Failed to build the King Phisher msi package
	echo Error level: %ERRORLEVEL%
	exit /b %ERRORLEVEL%
)

:: build complete, calculate the time elapsed
set end=%time%
set options="tokens=1-4 delims=:."
for /f %options% %%a in ("%start%") do set start_h=%%a&set /a start_m=100%%b %% 100&set /a start_s=100%%c %% 100&set /a start_ms=100%%d %% 100
for /f %options% %%a in ("%end%") do set end_h=%%a&set /a end_m=100%%b %% 100&set /a end_s=100%%c %% 100&set /a end_ms=100%%d %% 100

set /a hours=%end_h%-%start_h%
set /a mins=%end_m%-%start_m%
set /a secs=%end_s%-%start_s%
set /a ms=%end_ms%-%start_ms%
if %hours% lss 0 set /a hours = 24%hours%
if %mins% lss 0 set /a hours = %hours% - 1 & set /a mins = 60%mins%
if %secs% lss 0 set /a mins = %mins% - 1 & set /a secs = 60%secs%
if %ms% lss 0 set /a secs = %secs% - 1 & set /a ms = 100%ms%
if 1%ms% lss 100 set ms=0%ms%

:: mission accomplished
set /a totalsecs = %hours%*3600 + %mins%*60 + %secs%
echo build completed in %hours%:%mins%:%secs%.%ms% (%totalsecs%.%ms%s total)

echo the generated exe is located in the build/ directory
echo the generated msi is located in the dist/ directory
