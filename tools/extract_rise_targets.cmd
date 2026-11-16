@echo off
rem =====================================================================
rem  extract_rise_targets.cmd
rem  One-shot targeted extraction of MHRise static AI assets for em131.
rem  Runs the main pak, then the RE Engine patch pak (patch wins on same
rem  names via --override). Pure ASCII and GBK-safe, CRLF line endings.
rem  Echo-line metacharacters are caret-escaped per project convention.
rem  Usage: pass a main pak full path as arg 1 to override the default.
rem         Set DO_TEST=0 near the top to skip the memory-only precheck.
rem =====================================================================
cd /d "%~dp0..\.."
set "ROOT=%CD%"

set "PAK=D:\Steam\steamapps\common\MonsterHunterRise\re_chunk_000.pak"
set "PAKPATCH=D:\Steam\steamapps\common\MonsterHunterRise\re_chunk_000.pak.patch_001.pak"
if not "%~1"=="" set "PAK=%~1"
set "DO_TEST=1"
set "TOOL=00_Tools\06_REEngine_Pak\ree-pak-cli.exe"
set "LIST=00_Tools\06_REEngine_Pak\assets\filelist\MHR_STM_Release.list"
set "UNPACK=04_RiseAI\refs\rise_target_unpack"
set "JSONOUT=04_RiseAI\out\rsz_target_json"

echo.
echo [RISE] Targeted MHRise static AI extract -^> %ROOT%\04_RiseAI
echo [RISE] PAK      : %PAK%
echo [RISE] PAKPATCH : %PAKPATCH%
echo [RISE] LIST     : %LIST% - lowercase natives/stm
echo [RISE] Filter groups: hub main, think main, range^|stamina, action^|combo
echo [RISE] NOTE: 442 manifest uses uppercase natives/STM; filelist uses lowercase.
echo.

rem Keep existence checks as hints only - do not hard-exit if a pak is absent.
if not exist "%PAK%" echo [RISE] HINT: main pak not found at default path; pass a full path as arg 1.
if not exist "%PAKPATCH%" echo [RISE] HINT: patch pak not found; patch step will be skipped.
if not exist "%TOOL%" echo [RISE] HINT: ree-pak-cli.exe not found -^> %TOOL%
if not exist "%LIST%" echo [RISE] HINT: filelist not found -^> %LIST%
echo.

echo [RISE] PRECHECK  regex hit count, memory only, no disk writes
if "%DO_TEST%"=="0" goto :skiptest
"%TOOL%" unpack -p "%LIST%" -i "%PAK%" -f em131/00/ai_fsm_user_data/hub/.*_main\.user\.2^|em131/00/ai_fsm_user_data/think/.*_main\.user\.2^|em131/00/user_data/em131_00_range_data\.user\.2^|em131/00/user_data/em131_00_stamina_data\.user\.2^|em131/common/act_tbl_user_data/action/.*\.user\.2^|em131/common/act_tbl_user_data/combo/.*\.user\.2 --backend mmap --test
if errorlevel 1 goto :testfail
:skiptest

echo [RISE] STEP 1/3  main pak unpack -^> %UNPACK%
"%TOOL%" unpack -p "%LIST%" -i "%PAK%" -o "%UNPACK%" -f em131/00/ai_fsm_user_data/hub/.*_main\.user\.2^|em131/00/ai_fsm_user_data/think/.*_main\.user\.2^|em131/00/user_data/em131_00_range_data\.user\.2^|em131/00/user_data/em131_00_stamina_data\.user\.2^|em131/common/act_tbl_user_data/action/.*\.user\.2^|em131/common/act_tbl_user_data/combo/.*\.user\.2 --backend mmap --override --skip-unknown
if errorlevel 1 goto :unpackfail

echo [RISE] STEP 2/3  patch pak unpack -^> %UNPACK% - override same names
if not exist "%PAKPATCH%" goto :skippatch
"%TOOL%" unpack -p "%LIST%" -i "%PAKPATCH%" -o "%UNPACK%" -f em131/00/ai_fsm_user_data/hub/.*_main\.user\.2^|em131/00/ai_fsm_user_data/think/.*_main\.user\.2^|em131/00/user_data/em131_00_range_data\.user\.2^|em131/00/user_data/em131_00_stamina_data\.user\.2^|em131/common/act_tbl_user_data/action/.*\.user\.2^|em131/common/act_tbl_user_data/combo/.*\.user\.2 --backend mmap --override --skip-unknown
if errorlevel 1 goto :unpackfail
:skippatch

echo [RISE] STEP 3/3  rsz parse -^> %JSONOUT%
python -c "import sys,json,pathlib; sys.path.insert(0,'04_RiseAI/tools'); import rsz_parse; out=pathlib.Path('04_RiseAI/out/rsz_target_json'); out.mkdir(parents=True,exist_ok=True); src=pathlib.Path('04_RiseAI/refs/rise_target_unpack'); fs=sorted(src.rglob('*.user.2')); print('[RISE]   parsing',len(fs),'files'); [ (out/(p.name+'.json')).write_text(json.dumps(rsz_parse.parse(str(p)),ensure_ascii=False,indent=1),encoding='utf-8') for p in fs ]; print('[RISE]   wrote',len(fs),'JSON to',str(out))"
if errorlevel 1 goto :parsefail

echo.
echo [RISE] DONE. 12 files expected. Scalars are trustworthy; object refs are
echo [RISE] raw 4-byte values and cannot by themselves prove a Hub-to-pool chain.
echo [RISE] rsz_parse.py --json-out CLI is buggy: it also parses the output dir
echo [RISE] as an input file; STEP 3 imports parse directly - same workaround
echo [RISE] as tools/extract_rise_facts.py. See out/rise_target_extract_plan.md
exit /b 0

:testfail
echo [RISE] ERROR: --test precheck failed. Check pak path, list path, and -f regex.
exit /b 1

:unpackfail
echo [RISE] ERROR: unpack failed. Check pak integrity, list path, and -f regex.
exit /b 1

:parsefail
echo [RISE] ERROR: parse failed. Check python + 04_RiseAI/refs/rszmhrise.json
exit /b 1
