@echo off
rem 어느 폴더에서 실행하든 이 프로젝트의 venv 파이썬을 쓴다
"%~dp0.venv\Scripts\python.exe" "%~dp0run.py" %*
