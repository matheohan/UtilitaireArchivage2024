# -*- coding: utf-8 -*-

import os
import requests
import logging
import json
import zipfile
import hashlib
import tarfile 

import paramiko
import time

def load_config(config_path='config.json'):
    with open(config_path, 'r') as config_file:
        return json.load(config_file)

def download_zip_file(url, destination):
    try:
        head_response = requests.head(url, allow_redirects=True, verify=False, timeout=5)
        head_response.raise_for_status()
    except requests.RequestException as e:
        raise Exception(f"Erreur lors de la vérification de l'URL : {url}")

    try:
        response = requests.get(url, stream=True, verify=False)
        response.raise_for_status()

        with open(destination, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        logging.info(f"Téléchargement réussi : {destination}")
    except requests.RequestException as e:
        raise Exception(f"Erreur lors du téléchargement : {e}")


def extract_zip(zip_path, target_file):
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        if target_file in zip_ref.namelist():
            zip_ref.extract(target_file, os.path.dirname(zip_path))
            logging.info(f"Fichier extrait : {target_file}")
        else:
            raise Exception(f"{target_file} introuvable dans l'archive {zip_path}")

def calculate_file_hash(file_path):
    sha256_hash = hashlib.sha256()
    with open(file_path, 'rb') as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()

def save_hash(hash_value, hash_file):
    with open(hash_file, 'w') as f:
        f.write(hash_value)

def is_new_file(current_hash, hash_file):
    try:
        with open(hash_file, 'r') as f:
            last_hash = f.read()
            return current_hash != last_hash
    except FileNotFoundError:
        # Si le fichier n'existe pas, c'est la première exécution
        return True

def create_tgz_archive(source_file, archive_name):
    with tarfile.open(archive_name, "w:gz") as tar:
        tar.add(source_file, arcname=os.path.basename(source_file))
    logging.info(f"Archive créée : {archive_name}")

def upload_to_sftp(archive_name, server_config):
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