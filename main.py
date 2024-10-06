# -*- coding: utf-8 -*-

import os
import logging
from datetime import datetime
from functions import *


try:
    # 0. Initialisation
    # Chargement de la configuration
    config = load_config()

    # Vérification de l'existence du dossier logs
    if not os.path.exists(f"./{config['logs_directory_name']}"):
        os.makedirs(f"./{config['logs_directory_name']}")

    # Configuration du logging
    logging.basicConfig(filename=f"./{config['logs_directory_name']}/{config['log_file_name']}", level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s', encoding='utf-8')

    # 1. Téléchargement du fichier .zip
    # Vérification de l'existence du dossier files
    if not os.path.exists(f"./{config['files_directory_name']}"):
        os.makedirs(f"./{config['files_directory_name']}")

    file_path = f"./{config['files_directory_name']}/{config['remote_file_name']}"
    download_zip_file(f"{config['remote_host_server_url']}/{config['remote_file_name']}", file_path)
    
    # 2. Décompression et vérification du contenu
    extract_zip(file_path, config['extracted_file_name'])

    # 3. Calcul du hash du fichier SQL extrait
    extracted_file_path = f"./{config['files_directory_name']}/{config['extracted_file_name'].split('/')[-1]}"
    current_hash = calculate_file_hash(extracted_file_path)

    # 4. Vérifier si le fichier est nouveau
    hash_file_path = f"./{config['files_directory_name']}/{config['hash_file_name']}"
    if is_new_file(current_hash, hash_file_path):
        logging.info("Nouveau fichier détecté, lancement de l'archivage.")

        # Sauvegarder le hash du fichier actuel pour la prochaine comparaison
        save_hash(current_hash, hash_file_path)

        # 5. Création de l'archive
        archive_name = f"{datetime.now().strftime('%Y%m%d')}.tgz"
        create_tgz_archive(extracted_file_path, archive_name)

        # 6. Transfert de l'archive vers le serveur distant
        if config['server']['type'] == 'sftp':
            upload_to_sftp(archive_name, config['server'])
    else:
        logging.info("Le fichier est identique à celui de la veille.")

    # 7. Gestion de la durée de rétention
    clean_old_archives(config['retention_days'], config['server'], )

except Exception as e:
    logging.error(f"Erreur lors de l'exécution : {e}")