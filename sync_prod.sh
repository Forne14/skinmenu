#!/bin/bash

# Configuration
REMOTE_USER="deploy"
REMOTE_HOST="91.99.125.39"
SSH_KEY="$HOME/.ssh/hetzner_ed25519"
REMOTE_DIR="/home/deploy/apps/skinmenu"
LOCAL_DIR="/Users/yeerus/Repos/Tego/skinmenu"

# Colors for output
GREEN='\033[0;32m'
NC='\033[0m' # No Color

echo -e "${GREEN}1. Creating safe database copy on server...${NC}"
# FIX: Use 'cp' because sqlite3 is not installed on the server
ssh -i $SSH_KEY $REMOTE_USER@$REMOTE_HOST "cd $REMOTE_DIR && cp db.sqlite3 db_sync_copy.sqlite3"

echo -e "${GREEN}2. Downloading database copy...${NC}"
scp -i $SSH_KEY $REMOTE_USER@$REMOTE_HOST:$REMOTE_DIR/db_sync_copy.sqlite3 $LOCAL_DIR/db.sqlite3

echo -e "${GREEN}3. Syncing media files...${NC}"
rsync -avz -e "ssh -i $SSH_KEY" $REMOTE_USER@$REMOTE_HOST:$REMOTE_DIR/media/ $LOCAL_DIR/media/

echo -e "${GREEN}4. Cleaning up remote copy...${NC}"
ssh -i $SSH_KEY $REMOTE_USER@$REMOTE_HOST "rm $REMOTE_DIR/db_sync_copy.sqlite3"

echo -e "${GREEN}5. Updating Wagtail Site settings to localhost:8000...${NC}"
# We export the key here so the python command below works
export DJANGO_SECRET_KEY='django-insecure-local-sync-key'

cd $LOCAL_DIR
python3 manage.py shell <<EOF
from wagtail.models import Site
site = Site.objects.filter(is_default_site=True).first()
if site:
    site.hostname = 'localhost'
    site.port = 8000
    site.save()
    print(f"   Success: Site updated to {site.hostname}:{site.port}")
else:
    print("   Warning: No default site found.")
EOF

echo -e "${GREEN}✅ Sync complete! Restart runserver now.${NC}"