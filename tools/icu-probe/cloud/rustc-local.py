#!/usr/bin/env python3
"""Tracked launcher for the official project-local rustc."""

from rust_loader import exec_tool


if __name__ == "__main__":
    exec_tool("rustc")
