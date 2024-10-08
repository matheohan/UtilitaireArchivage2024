#!/bin/bash

###--- Dependencies and Cron Setup ---###

# Install paramiko
apt install python3-paramiko -y

# Install jq and sshpass
apt install jq sshpass -y 

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

###--- SSH KEY Setup ---###
# Function to read JSON file and extract configuration
read_config() {
    local json_file="$1"
    remote_host=$(jq -r '.remote_host_server_url' "$json_file")
    username=$(jq -r '.server.username' "$json_file")
    password=$(jq -r '.server.password' "$json_file")
    hostname=$(jq -r '.server.hostname' "$json_file")
    port=$(jq -r '.server.port' "$json_file")
}

update_config_file() {
    local json_file="$1"
    local temp_file="${json_file}.tmp"
    
    jq '.server.password = ""' "$json_file" > "$temp_file" && mv "$temp_file" "$json_file"
}

# Function to create SSH key
create_ssh_key() {
    ssh-keygen -t rsa -b 4096 -f ~/.ssh/id_rsa -N ""
}

# Function to add public key to remote server
add_public_key_to_server() {
    local remote_server="$1"
    if [ -n "$password" ]; then
        sshpass -p "$password" ssh-copy-id -o StrictHostKeyChecking=no -p "$port" "$username@$remote_server"
        # Immediately unset the password after use
        update_config_file "$config_file"
    else
        echo "Error: Password is not set in the configuration file."
        exit 1
    fi
}

###--- Main script ---###
config_file="config.json"

# Read configuration from JSON file
read_config "$config_file"

# Create SSH key if it doesn't exist
if [ ! -f ~/.ssh/id_rsa ]; then
    create_ssh_key
fi

# Add public key to remote server
if [ -n "$hostname" ]; then
    add_public_key_to_server "$hostname"
else
    echo "Error: Hostname is not specified in the configuration file."
    exit 1
fi