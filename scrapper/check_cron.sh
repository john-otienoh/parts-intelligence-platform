#!/bin/bash
echo "=== Last 3 runs ==="
grep "Scheduled run complete" logs/scraper.log | tail -3

echo ""
echo "=== Last error (if any) ==="
tail -5 logs/scraper_error.log 2>/dev/null || echo "No errors"