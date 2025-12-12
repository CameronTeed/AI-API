#!/bin/bash

# start-data-collection.sh
# Helper script to start PostgreSQL and run data collection
# Uses the same environment variables as the main application

set -e

echo "╔════════════════════════════════════════════════════════════════════════════╗"
echo "║                                                                            ║"
echo "║                  🌍 DATA COLLECTION HELPER SCRIPT                         ║"
echo "║                                                                            ║"
echo "║              Starts PostgreSQL and runs data collection                   ║"
echo "║                                                                            ║"
echo "╚════════════════════════════════════════════════════════════════════════════╝"
echo ""

# Load environment variables from .env
if [ -f ".env" ]; then
    echo "📄 Loading environment variables from .env..."
    # Load .env file, filtering out comments and empty lines
    set -a
    source <(grep -v '^#' .env | grep -v '^$' | sed 's/^/export /')
    set +a
else
    echo "⚠️  .env file not found in current directory"
    echo "   Creating .env with default values..."
    cat > .env << 'EOF'
# Database Configuration
DB_HOST=localhost
DB_PORT=5432
DB_NAME=sparkdates
DB_USER=postgres
DB_PASSWORD=postgres

# Google Places API
GOOGLE_PLACES_API_KEY=your_api_key_here

# Application Settings
DEFAULT_CITY=Ottawa
EOF
    echo "✅ Created .env file - please update GOOGLE_PLACES_API_KEY"
    exit 1
fi

echo ""
echo "🔍 Checking database configuration..."
echo "   Host: $DB_HOST"
echo "   Port: $DB_PORT"
echo "   Database: $DB_NAME"
echo "   User: $DB_USER"

# Check if using local or remote database
if [[ "$DB_HOST" == "localhost" || "$DB_HOST" == "127.0.0.1" ]]; then
    echo ""
    echo "🔍 Checking PostgreSQL status (local)..."
    if pg_isready -h "$DB_HOST" -p "$DB_PORT" > /dev/null 2>&1; then
        echo "✅ PostgreSQL is already running"
    else
        echo "❌ PostgreSQL is not running"
        echo ""
        echo "🚀 Starting PostgreSQL..."

        # Try different methods to start PostgreSQL
        if command -v systemctl &> /dev/null; then
            echo "   Using systemctl..."
            sudo systemctl start postgresql || true
        elif command -v service &> /dev/null; then
            echo "   Using service..."
            sudo service postgresql start || true
        else
            echo "   ⚠️  Could not find systemctl or service command"
            echo "   Please start PostgreSQL manually:"
            echo "   - Linux: sudo systemctl start postgresql"
            echo "   - macOS: brew services start postgresql"
            echo "   - Docker: docker run -d --name postgres -e POSTGRES_PASSWORD=postgres -p 5432:5432 postgres:15"
            exit 1
        fi

        # Wait for PostgreSQL to start
        echo "   Waiting for PostgreSQL to start..."
        sleep 3

        # Check again
        if pg_isready -h "$DB_HOST" -p "$DB_PORT" > /dev/null 2>&1; then
            echo "✅ PostgreSQL started successfully"
        else
            echo "❌ PostgreSQL failed to start"
            echo "   Please start PostgreSQL manually and try again"
            exit 1
        fi
    fi

    echo ""
    echo "🔐 Verifying database connection..."
    if psql -h "$DB_HOST" -U "$DB_USER" -d "$DB_NAME" -c "SELECT 1;" > /dev/null 2>&1; then
        echo "✅ Database connection successful"
    else
        echo "⚠️  Database '$DB_NAME' does not exist or connection failed"
        echo "   Creating database..."
        psql -h "$DB_HOST" -U "$DB_USER" -c "CREATE DATABASE $DB_NAME;" 2>/dev/null || true
        echo "✅ Database created or already exists"
    fi
else
    echo ""
    echo "🌐 Using remote database (Supabase)"
    echo "✅ Skipping local PostgreSQL checks"
    echo "✅ Database connection will be handled by the script"
    echo "✅ Using same connection as main application"
fi

echo ""
echo "🌍 Starting data collection..."
echo "   This will take 2-3 hours to complete (150+ search queries)"
echo "   Automatic rate limiting: 1 second between queries"
echo ""

# Run the data collection script
PYTHONPATH=. python3 final/fetch_and_store_venues.py

echo ""
echo "✅ Data collection complete!"
echo ""
echo "📊 Verify data:"
echo "   psql -h $DB_HOST -U $DB_USER -d $DB_NAME -c \"SELECT COUNT(*) FROM venues;\""

