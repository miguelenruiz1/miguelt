#!/bin/sh
chown -R invsvc:invsvc /app/uploads 2>/dev/null || true
exec gosu invsvc "$@"
