# Halcyon Inventory API

A Django REST API for supplier, product, category, and inventory-movement management. JWT authentication protects the API; staff users administer the catalog, and standard users can manage their own stock movements.

## Run locally

```sh
docker compose up --build
```

The API is available at `http://localhost:8000`. OpenAPI is served at `/api/docs/` and the schema at `/api/schema/`. Create a staff account with `docker compose exec app python manage.py createsuperuser`; standard accounts can be created through Django admin or the user-management process used by your deployment.

Compose includes development-only database and Django secret defaults. Set strong `DB_PASSWORD` and `DJANGO_SECRET_KEY` values in the environment before deploying beyond a local environment.

For a local Python run, use Python 3.12+, create a virtual environment, install `requirements.txt`, set `DJANGO_SECRET_KEY`, then run `python manage.py migrate` and `python manage.py runserver`. SQLite is the default for this development path. The Compose and CI paths use PostgreSQL.

## Authentication and examples

Obtain a JWT pair for an existing user:

```sh
curl -X POST http://localhost:8000/api/token/ \
  -H 'Content-Type: application/json' \
  -d '{"username":"warehouse-user","password":"your-password"}'
```

Use the returned access token on authenticated endpoints:

```sh
export TOKEN='your-access-token'
curl http://localhost:8000/api/products/ -H "Authorization: Bearer $TOKEN"
curl -X POST http://localhost:8000/api/transactions/ \
  -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
  -d '{"product":1,"movement":"IN","quantity":25,"reference":"PO-1042"}'
curl http://localhost:8000/health/
```

Staff users can create, update, and delete suppliers, categories, and products. Authenticated standard users can read the catalog and create, read, update, or delete their own movements. `IN` increases stock and `OUT` decreases it; an outbound movement cannot reduce stock below zero. Staff can administer all movements. Error responses use `{"error":{"code":"...","message":"...","details":{...}}}`.

## Index choices

Product SKU is unique and indexed because it is the primary operational lookup key. Product name and SKU each have explicit indexes to support catalog search. Supplier and category foreign keys are indexed by Django, supporting supplier/category filtering and joins. Movement indexes on `(product, created_at)` support product ledger queries in chronological order; `(created_by, created_at)` supports a user's recent movement history. These indexes follow the API's expected lookup and ordering patterns while avoiding indexes on low-selectivity movement types.

## Checks

```sh
python manage.py test inventory
coverage run python manage.py test inventory
coverage report --fail-under=80
flake8 .
```

CI runs the same lint, test, and coverage gates against PostgreSQL before building the production image.