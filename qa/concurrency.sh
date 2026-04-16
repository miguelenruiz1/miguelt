#!/bin/bash
JWT="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJmMWMwNGNjMi1hYTk0LTQxM2UtYTBkOC02NzI1MWIzZmYyZWUiLCJ0ZW5hbnRfaWQiOiJpc28tYS0yMWY3M2UiLCJ0eXBlIjoiYWNjZXNzIiwiaWF0IjoxNzc2MjE1MDQ3LCJleHAiOjE3NzYyNDM4NDd9.YC0phZWI9RZpisCj2eecIW7t94qsgGe2X_vPQWRVzMc"
CODE="$1"
curl -s -o /dev/null -w "%{http_code}\n" -X POST "http://localhost:9000/api/v1/compliance/plots/" \
  -H "Authorization: Bearer $JWT" -H "X-Tenant-Id: iso-a-21f73e" -H "Content-Type: application/json" \
  -d "{\"plot_code\":\"$CODE\",\"producer_name\":\"Conc\",\"country_code\":\"CO\",\"commodity_type\":\"coffee\",\"plot_area_ha\":2.0,\"geolocation_type\":\"point\",\"lat\":2.123456,\"lng\":-75.123456}"
