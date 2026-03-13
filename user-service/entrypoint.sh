#!/bin/sh
chown -R usersvc:usersvc /app/uploads 2>/dev/null || true
exec gosu usersvc "$@"
