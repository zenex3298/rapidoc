#!/bin/bash
# Heroku deployment helper script

set -e  # Exit immediately if a command exits with a non-zero status

echo "===== RapidocsAI Heroku Deployment Helper ====="
echo ""

# Check if Heroku CLI is installed
if ! command -v heroku &> /dev/null; then
    echo "Heroku CLI not found. Please install it first:"
    echo "Visit: https://devcenter.heroku.com/articles/heroku-cli"
    exit 1
fi

# Check if logged into Heroku
if ! heroku auth:whoami &> /dev/null; then
    echo "Not logged into Heroku. Please login first:"
    heroku login
fi

# Check for required environment variables
echo "Checking for required environment variables..."

# Check for .env file
if [ ! -f .env ]; then
    echo "ERROR: .env file not found!"
    echo "Please make sure you have a .env file with all required environment variables."
    exit 1
fi

# Load .env file
set -a
source .env
set +a

# Check required variables
REQUIRED_VARS=("JWT_SECRET_KEY" "AWS_ACCESS_KEY_ID" "AWS_SECRET_ACCESS_KEY" "S3_BUCKET_NAME" "OPENAI_API_KEY")
MISSING_VARS=0

for VAR in "${REQUIRED_VARS[@]}"; do
    if [ -z "${!VAR}" ]; then
        echo "Missing required environment variable: $VAR"
        MISSING_VARS=1
    fi
done

if [ $MISSING_VARS -eq 1 ]; then
    echo "Please fill in the missing environment variables in .env file."
    exit 1
fi

# Set app name without prompt
APP_NAME="rapidocsai"
echo "Using Heroku app name: $APP_NAME"

# Create Heroku app
echo "Creating Heroku app: $APP_NAME..."
heroku create $APP_NAME || echo "App may already exist, continuing..."

# Add PostgreSQL
echo "Adding PostgreSQL addon..."
heroku addons:create heroku-postgresql:mini --app $APP_NAME || echo "PostgreSQL may already exist, continuing..."

# Configure environment variables
echo "Setting environment variables..."
heroku config:set JWT_SECRET_KEY="$JWT_SECRET_KEY" --app $APP_NAME
heroku config:set OPENAI_API_KEY="$OPENAI_API_KEY" --app $APP_NAME
heroku config:set USE_S3_STORAGE=true --app $APP_NAME
heroku config:set AWS_ACCESS_KEY_ID="$AWS_ACCESS_KEY_ID" --app $APP_NAME
heroku config:set AWS_SECRET_ACCESS_KEY="$AWS_SECRET_ACCESS_KEY" --app $APP_NAME
heroku config:set AWS_REGION="${AWS_REGION:-us-east-1}" --app $APP_NAME
heroku config:set S3_BUCKET_NAME="$S3_BUCKET_NAME" --app $APP_NAME
heroku config:set ENVIRONMENT=production --app $APP_NAME
heroku config:set OPENAI_MODEL="${OPENAI_MODEL:-gpt-4o}" --app $APP_NAME
heroku config:set OPENAI_TEMPERATURE="${OPENAI_TEMPERATURE:-0.3}" --app $APP_NAME
heroku config:set LOG_LEVEL="${LOG_LEVEL:-INFO}" --app $APP_NAME

# Set Heroku as Git remote
echo "Setting Heroku Git remote..."
heroku git:remote -a $APP_NAME

# Automatically deploy without prompt
echo "Automatically deploying to Heroku..."

# Push to Heroku
echo "Deploying to Heroku..."
git push heroku master

# Run migrations
echo "Running database migrations..."
heroku run python -m alembic upgrade head --app $APP_NAME

echo ""
echo "===== Deployment completed ====="
echo "Your app is available at: https://$APP_NAME.herokuapp.com"
echo ""
echo "Use these commands for monitoring and maintenance:"
echo "  heroku logs --tail --app $APP_NAME             # View logs"
echo "  heroku ps --app $APP_NAME                     # Check app status"
echo "  heroku pg:psql --app $APP_NAME                # Access PostgreSQL"
echo "  heroku restart --app $APP_NAME                # Restart application"