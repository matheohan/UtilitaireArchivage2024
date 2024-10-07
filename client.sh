#!/bin/bash

# Install paramiko
apt install python3-paramiko

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" &> /dev/null && pwd)"

# Define the Python script path relative to the script directory
PYTHON_SCRIPT="$SCRIPT_DIR/main.py"

# Define the cron schedule
CRON_SCHEDULE="* * * * *"

# Create the cron job command
CRON_COMMAND="cd $SCRIPT_DIR && /usr/bin/python3 $PYTHON_SCRIPT >> $SCRIPT_DIR/cron_log.txt 2>&1"

# Combine schedule and command
CRON_JOB="$CRON_SCHEDULE $CRON_COMMAND"

# Function to add or update the cron job
update_cron() {
    # Check if the cron job already exists
    existing_job=$(crontab -l | grep -F "$PYTHON_SCRIPT")
    
    if [ -n "$existing_job" ]; then
        # Update existing job
        (crontab -l | sed "s|$existing_job|$CRON_JOB|") | crontab -
        echo "Cron job updated."
    else
        # Add new job
        (crontab -l 2>/dev/null; echo "$CRON_JOB") | crontab -
        echo "Cron job added."
    fi
}

# Run the function to update crontab
update_cron

# Print the working directory for verification
echo "Working directory set to: $SCRIPT_DIR"

# Restart the cron service
systemctl restart cron

# Enable the cron service to start on boot
systemctl enable cron