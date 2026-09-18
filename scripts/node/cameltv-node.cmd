@echo off
rem cameltv-node: one-command start (Windows). Usage: cameltv-node up --node-id my-pc
rem Keep this file ASCII-only: cmd.exe mis-parses UTF-8 comments on some code pages.
python "%~dp0cameltv_node\cli.py" %*
