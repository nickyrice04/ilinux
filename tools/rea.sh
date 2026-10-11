#!/bin/sh
# Run the project-local REA CLI (never `setup`/`update`; see .claude/settings.json deny rules).
exec /opt/homebrew/bin/node "$(dirname "$0")/rea/node_modules/rea-agents/scripts/rea.mjs" "$@"
