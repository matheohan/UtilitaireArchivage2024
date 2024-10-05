# functions.py

import os
import requests # marche avec Python 3.8.3 ('base': conda)
import zipfile
import tarfile 
import hashlib
import paramiko # marche avec Python 3.8.3 ('base': conda)
import logging
import time

def load_config(config_path='config.json'):
    """Charge la configuration depuis le fichier JSON spécifié."""
    import json
    with open(config_path, 'r') as config_file:
        return json.load(config_file)

def download_zip_file(url, destination):
    """Télécharge le fichier .zip depuis l'URL et le sauvegarde dans le chemin spécifié."""
    response = requests.get(url, stream=True)
    if response.status_code == 200:
        with open(destination, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        logging.info(f"Téléchargement réussi : {destination}")
    else:
        raise Exception(f"Erreur de téléchargement, statut : {response.status_code}")

def extract_zip(zip_path, target_file):
    """Extrait le fichier cible depuis l'archive .zip."""
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        if target_file in zip_ref.namelist():
            zip_ref.extract(target_file, os.path.dirname(zip_path))
            logging.info(f"Fichier extrait : {target_file}")
        else:
            raise Exception(f"{target_file} introuvable dans l'archive {zip_path}")

def calculate_file_hash(file_path):
    """Calcule le hash SHA256 d'un fichier donné."""
    sha256_hash = hashlib.sha256()
    with open(file_path, 'rb') as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()

def save_hash(hash_value, hash_file):
    """Sauvegarde le hash dans un fichier texte."""
    with open(hash_file, 'w') as f:
        f.write(hash_value)

def is_new_file(current_hash, hash_file):
    """Compare le hash du fichier actuel avec celui de la veille."""
    try:
        with open(hash_file, 'r') as f:
            last_hash = f.read()
            return current_hash != last_hash
    except FileNotFoundError:
        # Si le fichier n'existe pas, c'est la première exécution
        return True

def create_tgz_archive(source_file, archive_name):
    """Crée une archive .tgz avec le fichier source."""
    with tarfile.open(archive_name, "w:gz") as tar:
        tar.add(source_file, arcname=os.path.basename(source_file))
    logging.info(f"Archive créée : {archive_name}")

def upload_to_sftp(archive_name, server_config):
    """Transfère le fichier .tgz vers un serveur SFTP."""
    try:
        transport = paramiko.Transport((server_config['host'], server_config['port']))
        transport.connect(username=server_config['username'], password=server_config['password'])
        sftp = paramiko.SFTPClient.from_transport(transport)
        destination = os.path.join(server_config['destination_path'], archive_name)
        sftp.put(archive_name, destination)
        logging.info(f"Fichier {archive_name} transféré avec succès vers {server_config['host']}")
        sftp.close()
        transport.close()
    except Exception as e:
        logging.error(f"Erreur lors du transfert SFTP : {e}")
        raise e

def clean_old_archives(server_config, retention_days):
    """Supprime les fichiers anciens dépassant la durée de rétention."""
    try:
        transport = paramiko.Transport((server_config['host'], server_config['port']))
        transport.connect(username=server_config['username'], password=server_config['password'])
        sftp = paramiko.SFTPClient.from_transport(transport)
        
        retention_seconds = retention_days * 24 * 60 * 60
        now = time.time()
        
        for file in sftp.listdir(server_config['destination_path']):
            file_path = os.path.join(server_config['destination_path'], file)
            if (now - sftp.stat(file_path).st_mtime) > retention_seconds:
                sftp.remove(file_path)
                logging.info(f"Fichier {file} supprimé (durée de rétention dépassée).")
        
        sftp.close()
        transport.close()
    except Exception as e:
        logging.error(f"Erreur lors de l'épuration des anciennes archives : {e}")
        raise e