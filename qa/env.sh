#!/bin/bash
# QA verification environment — 2026-04-14
export GATEWAY="http://localhost:9000"
export TENANT_ID="qaverifier-bdc8c6"
export JWT="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIzOGE4YzQ0OC04Yjg3LTQwZDItYTQ3Mi02MjY0YzIzOGQwMjAiLCJ0ZW5hbnRfaWQiOiJxYXZlcmlmaWVyLWJkYzhjNiIsInR5cGUiOiJhY2Nlc3MiLCJpYXQiOjE3NzYyMTE3NzIsImV4cCI6MTc3NjI0MDU3Mn0.B8tcKrhETCVWpjVRmXNOF2aApGiTrkqzQLFFa6JyPpA"
export USER_ID="38a8c448-8b87-40d2-a472-6264c238d020"
export A="Authorization: Bearer $JWT"
export T="X-Tenant-Id: $TENANT_ID"
export U="X-User-Id: $USER_ID"
export C="Content-Type: application/json"
