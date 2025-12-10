#!/bin/bash
# Quick database seeding script
# Usage: ./quick_seed.sh [option] [city]
# Options:
#   json    - Seed from JSON file (default)
#   google  - Seed from Google Places API
#   both    - Seed from both sources

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Load environment
if [ -f "$PROJECT_DIR/../.env" ]; then
    export $(cat "$PROJECT_DIR/../.env" | grep -v '^#' | xargs)
fi

echo -e "${BLUE}🌱 SparkDates Database Seeding${NC}"
echo "================================"

# Check if database is running
echo -e "${YELLOW}Checking database connection...${NC}"
if ! python3 -c "import psycopg2; psycopg2.connect(host='${DB_HOST:-localhost}', port='${DB_PORT:-5432}', database='${DB_NAME:-sparkdates_db}', user='${DB_USER:-postgres}', password='${DB_PASSWORD:-postgres}')" 2>/dev/null; then
    echo -e "${RED}❌ Database not accessible${NC}"
    echo "Make sure PostgreSQL is running:"
    echo "  docker-compose up -d postgres"
    exit 1
fi
echo -e "${GREEN}✅ Database connected${NC}"

# Determine seeding method
METHOD=${1:-json}
CITY=${2:-Ottawa}

case $METHOD in
    json)
        echo -e "${BLUE}📂 Seeding from JSON file...${NC}"
        python3 "$SCRIPT_DIR/seed_from_json.py" "$PROJECT_DIR/data/sample_date_ideas.json"
        ;;
    google)
        if [ -z "$GOOGLE_MAPS_API_KEY" ]; then
            echo -e "${RED}❌ GOOGLE_MAPS_API_KEY not set in .env${NC}"
            exit 1
        fi
        echo -e "${BLUE}🔍 Seeding from Google Places API for $CITY...${NC}"
        python3 "$SCRIPT_DIR/seed_database.py" "$CITY"
        ;;
    both)
        echo -e "${BLUE}📂 Seeding from JSON file...${NC}"
        python3 "$SCRIPT_DIR/seed_from_json.py" "$PROJECT_DIR/data/sample_date_ideas.json"
        
        if [ -z "$GOOGLE_MAPS_API_KEY" ]; then
            echo -e "${YELLOW}⚠️  Skipping Google Places (GOOGLE_MAPS_API_KEY not set)${NC}"
        else
            echo -e "${BLUE}🔍 Seeding from Google Places API for $CITY...${NC}"
            python3 "$SCRIPT_DIR/seed_database.py" "$CITY"
        fi
        ;;
    *)
        echo -e "${RED}Unknown option: $METHOD${NC}"
        echo "Usage: $0 [json|google|both] [city]"
        exit 1
        ;;
esac

echo ""
echo -e "${GREEN}✅ Seeding completed!${NC}"
echo ""
echo "Verify with:"
echo "  psql -h localhost -U postgres -d sparkdates_db -c 'SELECT COUNT(*) FROM event;'"

