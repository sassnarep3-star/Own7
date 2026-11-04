#!/usr/bin/env python3
"""Compatibility entrypoint; all public canonical pages have one generator.

The prior generator remains inspectable at incoming main commit 37e1bbd.
"""
from build_site import build
if __name__=='__main__':build()
