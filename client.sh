#!/bin/bash

###--- Dépendances et Configuration de Cron ---###

# Installation de paramiko
apt install python3-paramiko -y

# Installation de jq et sshpass
apt install jq sshpass -y 

# Obtention du répertoire où ce script est situé
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" &> /dev/null && pwd)"

# Définition du chemin du script Python relatif au répertoire du script
PYTHON_SCRIPT="$SCRIPT_DIR/main.py"

# Définition de l'interval cron
CRON_SCHEDULE="* * * * *"

# Création de la commande cron
CRON_COMMAND="cd $SCRIPT_DIR && /usr/bin/python3 $PYTHON_SCRIPT >> $SCRIPT_DIR/cron_log.txt 2>&1"

# Création de la tâche cron
CRON_JOB="$CRON_SCHEDULE $CRON_COMMAND"

# Fonction pour ajouter ou mettre à jour la tâche cron
update_cron() {
    # Vérification de l'existence de la tâche cron
    existing_job=$(crontab -l | grep -F "$PYTHON_SCRIPT")
    
    if [ -n "$existing_job" ]; then
        # Mise à jour de la tâche existante
        (crontab -l | sed "s|$existing_job|$CRON_JOB|") | crontab -
        echo "Tâche cron mise à jour."
    else
        # Ajouter d'une nouvelle tâche
        (crontab -l 2>/dev/null; echo "$CRON_JOB") | crontab -
        echo "Tâche cron ajoutée."
    fi
}

# Exécution de la fonction pour mettre à jour crontab
update_cron

# Affichage du répertoire de travail
echo "Répertoire de travail défini sur : $SCRIPT_DIR"

# Redémarrer le service cron
systemctl restart cron

# Activation du service cron pour qu'il démarre au démarrage
systemctl enable cron

###--- Configuration de la clé SSH ---###
# Fonction pour lire le fichier JSON et extraire la configuration associée
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

# Fonction pour créer une clé SSH
create_ssh_key() {
    ssh-keygen -t rsa -b 4096 -f ~/.ssh/id_rsa -N ""
}

# Fonction pour ajouter la clé publique au serveur distant
add_public_key_to_server() {
    local remote_server="$1"
    if [ -n "$password" ]; then
        sshpass -p "$password" ssh-copy-id -o StrictHostKeyChecking=no -p "$port" "$username@$remote_server"
        # Effacement immédiat du mot de passe après utilisation
        update_config_file "$config_file"
    else
        echo "Erreur : Le mot de passe n'est pas défini dans le fichier de configuration."
        exit 1
    fi
}

###--- Script principal ---###
config_file="config.json"

# Lecture de la configuration depuis le fichier JSON
read_config "$config_file"

# Création d'une clé SSH si elle n'existe pas
if [ ! -f ~/.ssh/id_rsa ]; then
    create_ssh_key
fi

# Ajout de la clé publique au serveur distant
if [ -n "$hostname" ]; then
    add_public_key_to_server "$hostname"
else
    echo "Erreur : Le nom d'hôte n'est pas spécifié dans le fichier de configuration."
    exit 1
fi