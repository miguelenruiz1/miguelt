#!/bin/sh
chown -R cmpsvc:cmpsvc /app/uploads 2>/dev/null || true
exec gosu cmpsvc "$@"
