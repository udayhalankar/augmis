#!/bin/bash
set -euo pipefail
: "${OPENAI_API_KEY:?Set OPENAI_API_KEY before running deploy-augmis.sh}"
: "${AUTH_JWT_SECRET:?Set AUTH_JWT_SECRET before running deploy-augmis.sh}"

cat > /home/ec2-user/augmis/backend.env <<EOFENV
OPENAI_API_KEY=${OPENAI_API_KEY}
AUTH_JWT_SECRET=${AUTH_JWT_SECRET}
OPENAI_MODEL=gpt-4.1-mini
OPENAI_EMBEDDING_MODEL=text-embedding-3-small
OCR_TESSERACT_CMD=/usr/bin/tesseract
VECTOR_BACKEND=pgvector
DATABASE_URL=postgresql+psycopg2://postgres:Test1234@augmis-db:5432/infomentica_dss
CORS_ALLOW_ORIGINS=https://app.augmis.com,https://www.augmis.com,http://localhost:3000,http://127.0.0.1:3000
AUTH_RESET_LINK_BASE_URL=https://app.augmis.com/reset-password
EOFENV
until [ "$(sudo docker inspect -f '{{.State.Health.Status}}' augmis-db 2>/dev/null || echo starting)" = "healthy" ]; do sleep 2; done
sudo docker rm -f augmis-backend >/dev/null 2>&1 || true
sudo docker run -d --name augmis-backend --network augmis-net --restart unless-stopped --env-file /home/ec2-user/augmis/backend.env -e DATABASE_URL=postgresql+psycopg2://postgres:Test1234@augmis-db:5432/infomentica_dss -v augmis-backend-storage:/app/storage -v augmis-uploaded-files:/app/uploaded_files -v augmis-index-store:/app/index_store -p 8001:8001 augmis-backend sh -c "python init_db.py && python seed_saas_data.py && uvicorn app.main:app --host 0.0.0.0 --port 8001"
