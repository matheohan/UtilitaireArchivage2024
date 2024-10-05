import os
import logging
from datetime import datetime
from functions import load_config, download_zip_file, extract_zip, calculate_file_hash, is_new_file, save_hash
from functions import create_tgz_archive, upload_to_sftp, clean_old_archives

# Charger la configuration
config = load_config()

# Configuration du logging
logging.basicConfig(filename=config['log_file'], level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Etapes principales
try:
    # 1. Téléchargement du fichier .zip
    download_zip_file(config['download_url'], config['local_zip_path'])

    # 2. Décompression et vérification du contenu
    extract_zip(config['local_zip_path'], config['extracted_sql_name'])

    # 3. Calcul du hash du fichier SQL extrait
    extracted_sql_path = os.path.join(os.path.dirname(config['local_zip_path']), config['extracted_sql_name'])
    current_hash = calculate_file_hash(extracted_sql_path)

    # 4. Vérifier si le fichier est nouveau
    if is_new_file(current_hash, config['hash_file_path']):
        logging.info("Nouveau fichier détecté, lancement de l'archivage.")

        # Sauvegarder le hash du fichier actuel pour la prochaine comparaison
        save_hash(current_hash, config['hash_file_path'])

        # 5. Création de l'archive
        archive_name = datetime.now().strftime(config['archive_name_format'])
        create_tgz_archive(config['extracted_sql_name'], archive_name)

        # 6. Transfert de l'archive vers le serveur distant
        if config['server']['type'] == 'sftp':
            upload_to_sftp(archive_name, config['server'])

        # 7. Gestion de la durée de rétention
        clean_old_archives(config['server'], config['retention_days'])
    else:
        logging.info("Le fichier est identique à celui de la veille. Fin du script.")
except Exception as e:
    logging.error(f"Erreur lors de l'exécution : {e}")