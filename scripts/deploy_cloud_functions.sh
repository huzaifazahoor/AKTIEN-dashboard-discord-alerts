#!/bin/bash

# Function to deploy a cloud function
deploy_function() {
    local function_name=$1
    local function_dir=$2
    local generation=$3
    local cron_syntax=${4:-""}
    local message_bodies=${5:-""}
    
    # Copy the common folder and requirements.txt to the function directory
    cp -r scripts/common $function_dir/
    cp scripts/requirements.txt $function_dir/

    # Deploying as a Cloud Function
    echo "Deploying $function_name as Cloud Function $generation..."

    # Base deployment command
    deployment_command="gcloud functions deploy $function_name \
        --region=us-central1 \
        --source=$function_dir \
        --runtime python311 \
        --trigger-http \
        --allow-unauthenticated \
        --set-env-vars DB_HOST=${DB_HOST},DB_PWD=${DB_PWD},DB_USER=${DB_USER},DB_NAME=${DB_NAME},FINVIZ_EMAIL=${FINVIZ_EMAIL} \
        --entry-point=main \
        --memory=4GiB \
        --cpu=2 \
        --concurrency=5 \
        --min-instances=0 \
        --max-instances=50"

    # Add generation-specific options
    if [ "$generation" = "no-gen2" ]; then
        deployment_command+=" --no-gen2"
        deployment_command+=" --docker-registry=artifact-registry"
        deployment_command+=" --timeout=540s"
    else
        deployment_command+=" --gen2"
        deployment_command+=" --timeout=3600s"
    fi

    # Execute the deployment command
    eval $deployment_command || { echo "Failed to deploy $function_name"; exit 1; }

    # Create Cloud Scheduler jobs for each message body (if provided)
    if [[ -n "$cron_syntax" && -n "$message_bodies" ]]; then
        local job_name_prefix="${function_name}-job-"
        
        # Convert message bodies into an array, splitting on '|'
        IFS='|' read -r -a message_array <<< "$message_bodies"

        for job_count in "${!message_array[@]}"; do 
            message_body="${message_array[$job_count]}"
            job_name="${job_name_prefix}${job_count}"
            echo "Creating Cloud Scheduler job $job_name for $function_name with message body: $message_body..."

            gcloud scheduler jobs create http $job_name \
                --schedule="$cron_syntax" \
                --time-zone="America/New_York" \
                --uri="https://us-central1-${PROJECT_ID}.cloudfunctions.net/$function_name" \
                --http-method="POST" \
                --headers="Content-Type=application/json" \
                --message-body="$message_body" \
                --location="us-central1" \
                --oidc-service-account-email="${SERVICE_ACCOUNT_EMAIL}" \
                --oidc-token-audience="https://us-central1-${PROJECT_ID}.cloudfunctions.net/$function_name" \
                --quiet \
                --attempt-deadline=30m
        done
    else
        echo "Skipping Cloud Scheduler job creation for $function_name (no cron syntax or message bodies provided)."
    fi

    # Clean up: remove the common folder and requirements.txt from the function directory
    rm -rf $function_dir/common
    rm -f $function_dir/requirements.txt
}

if git diff --name-only $GITHUB_BEFORE $GITHUB_SHA | grep -q 'scripts/1_earnings_discord_bot/'; then
    deploy_function "earnings_discord_bot_function" "scripts/1_earnings_discord_bot" "no-gen2" "05 16 * * MON-FRI" '{"hello": "world"}'
fi

if git diff --name-only $GITHUB_BEFORE $GITHUB_SHA | grep -q 'scripts/2_strong_earnings_bot/'; then
    deploy_function "strong_earnings_bot_function" "scripts/2_strong_earnings_bot" "no-gen2" "10 16 * * MON-FRI" '{"source":"strong_earnings"}'
fi

if git diff --name-only $GITHUB_BEFORE $GITHUB_SHA | grep -q 'scripts/3_momentum_gap_bot/'; then
    deploy_function "momentum_gap_bot_function" "scripts/3_momentum_gap_bot" "no-gen2" "15 16 * * MON-FRI" '{"source":"momentum_gap"}'
fi

if git diff --name-only $GITHUB_BEFORE $GITHUB_SHA | grep -q 'scripts/4_short_squeeze_bot/'; then
    deploy_function "short_squeeze_bot_function" "scripts/4_short_squeeze_bot" "no-gen2" "20 16 * * MON-FRI" '{"source":"short_squeeze"}'
fi

if git diff --name-only $GITHUB_BEFORE $GITHUB_SHA | grep -q 'scripts/5_technical_ma_bot/'; then
    deploy_function "technical_ma_bot_function" "scripts/5_technical_ma_bot" "no-gen2" "25 16 * * MON-FRI" '{"source":"technical_ma"}'
fi

if git diff --name-only $GITHUB_BEFORE $GITHUB_SHA | grep -q 'scripts/6_steady_performance_bot/'; then
    deploy_function "steady_performance_bot_function" "scripts/6_steady_performance_bot" "no-gen2" "30 16 * * MON-FRI" '{"source":"steady_performance"}'
fi