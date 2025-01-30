import json
import requests
import os
import shutil
import git
from zipfile import ZipFile
import tempfile
from pathlib import Path


def delete_all_folders(directory):
    try:
        for entry in os.listdir(directory):
            entry_path = os.path.join(directory, entry)
            if os.path.isdir(entry_path) and entry != '.git':
                shutil.rmtree(entry_path)
                print(f"Deleted directory: {entry_path}")
        print(f"All folders from '{directory}' have been deleted.")
    except Exception as e:
        print(f"Error deleting folders from '{directory}': {e}")

class AnypointJarDownloader:
    def __init__(self, client_id: str, client_secret: str, base_directory: str):
        self.base_url = "https://anypoint.mulesoft.com"
        self.access_token = None
        self.client_id = client_id
        self.client_secret = client_secret
        self.size_limit = 100 * 1024 * 1024  # 100MB in bytes
        self.base_directory = base_directory
        
    def authenticate(self):
        auth_url = f"{self.base_url}/accounts/api/v2/oauth2/token"
        data = {
            "grant_type": "client_credentials",
            "client_id": self.client_id,
            "client_secret": self.client_secret
        }
        response = requests.post(auth_url, headers={"Content-Type": "application/json"}, json=data)
        self.access_token = response.json()["access_token"]
        
    def get_business_group_id(self):
        response = requests.get(
            f"{self.base_url}/accounts/api/me",
            headers={"Authorization": f"Bearer {self.access_token}"}
        )
        return response.json()["user"]["organizationId"]

    def get_environments(self):
        url = f"{self.base_url}/accounts/api/organizations/{self.get_business_group_id()}/environments"
        headers = {"Authorization": f"Bearer {self.access_token}"}
        response = requests.get(url, headers=headers)
        return response.json()
        
    def get_applications(self, bg_id, env_id):
        url = f"{self.base_url}/cloudhub/api/v2/applications"
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "X-ANYPNT-ORG-ID": str(bg_id),
            "X-ANYPNT-ENV-ID": str(env_id)
        }
        response = requests.get(url, headers=headers)
        print(f"Apps response status: {response.status_code}")
        if response.status_code == 200:
            print(f"Number of applications found: {len(response.json())}")
        return response.json()

    def download_jar(self, app_name, env_id, env_name):
        env_path = os.path.join(self.base_directory, env_name)
        if not os.path.exists(env_path):
            os.makedirs(env_path)
                    
        bg_id = self.get_business_group_id()
        
        url = f"{self.base_url}/cloudhub/api/organizations/{bg_id}/environments/{env_id}/applications/{app_name}/download/application.jar"
        
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "X-ANYPNT-ORG-ID": str(bg_id),
            "X-ANYPNT-ENV-ID": str(env_id)
        }
        
        print(f"\nAttempting to download from: {url}")
        response = requests.get(url, headers=headers, stream=True)
        
        if response.status_code == 200:
            content_type = response.headers.get('content-type', '')
            print(f"Content-Type: {content_type}")
            
            file_path = os.path.join(env_path, f"{app_name}.jar")
            with open(file_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            print(f"Successfully downloaded {app_name}.jar")
            return True
        else:
            print(f"Download failed with status code: {response.status_code}")
            if response.status_code != 404:
                print(f"Response: {response.text[:200]}...")
            return False
    
    def organize_files(self, env_name):
        env_path = os.path.join(self.base_directory, env_name)
        print(f"\nOrganizing files for {env_name}...")
        
        # Create archive folder
        archive_path = os.path.normpath(os.path.join(env_path, 'archive_jars'))
        os.makedirs(archive_path, exist_ok=True)

        # Get all JAR files in the environment folder
        jar_files = [f for f in os.listdir(env_path) if f.endswith('.jar')]

        for jar_file in jar_files:
            print(f"\nProcessing {jar_file}")
            jar_path = os.path.normpath(os.path.join(env_path, jar_file))

            app_name = jar_file[:-4]  # Remove .jar extension
            app_path = os.path.normpath(os.path.join(env_path, app_name))
            
            try:
                # Create a temporary directory for extraction
                with tempfile.TemporaryDirectory() as temp_dir:
                    print(f"Extracting {jar_file} to temporary directory")
                    
                    # Extract everything to temp directory
                    with ZipFile(jar_path, 'r') as zip_ref:
                        for file_info in zip_ref.filelist:
                            try:
                                zip_ref.extract(file_info, temp_dir)
                            except OSError as e:
                                if getattr(e, 'winerror', None) == 206:  # Filename too long
                                    print(f"Skipping {file_info.filename}: Path too long")
                                    continue
                                else:
                                    continue
                    
                    # Look for mule-src directory
                    mule_src_path = os.path.join(temp_dir, "META-INF", "mule-src")
                    if os.path.exists(mule_src_path):
                        # Get the first directory in mule-src (should be application name)
                        app_dirs = [d for d in os.listdir(mule_src_path) 
                                if os.path.isdir(os.path.join(mule_src_path, d))]
                        
                        if app_dirs:
                            source_app_path = os.path.join(mule_src_path, app_dirs[0])
                            print(f"Found mule-src content in: {source_app_path}")
                            
                            # Create the target application directory
                            os.makedirs(app_path, exist_ok=True)
                            
                            # Copy everything from the source app directory to our target
                            def copy_directory(src, dst):
                                """Copy directory tree, skipping files with paths that are too long"""
                                for item in os.listdir(src):
                                    s = os.path.join(src, item)
                                    d = os.path.join(dst, item)
                                    
                                    if len(d) >= 260:  # Windows MAX_PATH limit
                                        print(f"Skipping {item}: Path too long")
                                        continue
                                        
                                    try:
                                        if os.path.isdir(s):
                                            os.makedirs(d, exist_ok=True)
                                            copy_directory(s, d)
                                        else:
                                            shutil.copy2(s, d)
                                    except OSError as e:
                                        if getattr(e, 'winerror', None) == 206:  # Filename too long
                                            print(f"Skipping {item}: Path too long")
                                        else:
                                            raise
                            
                            print(f"Copying mule-src contents to {app_path}")
                            copy_directory(source_app_path, app_path)
                            print(f"Successfully copied mule-src contents")
                        else:
                            print(f"No application directory found in mule-src for {jar_file}")
                    else:
                        print(f"No mule-src directory found in {jar_file}")
                # Check file size
                file_size = os.path.getsize(jar_path)
                if file_size > self.size_limit:
                    print(f"WARNING: {jar_file} is {file_size / (1024 * 1024):.2f}MB, exceeding the 100MB limit")
                    # Delete File
                    os.remove(jar_path)
                    print(f"Deleted oversized file: {jar_path}")
                else:
                    # Move original JAR to archive folder
                    archive_jar_path = os.path.normpath(os.path.join(archive_path, jar_file))
                    shutil.move(jar_path, archive_jar_path)
                    print(f"Moved {jar_file} to archive folder")
                
            except Exception as e:
                print(f"Error processing {jar_file}: {str(e)}")
                import traceback
                traceback.print_exc()

def cleanup_folders():
    """Removes design and staging folders if they exist"""
    folders_to_remove = ['design', 'staging']
    for folder in folders_to_remove:
        if os.path.exists(folder):
            try:
                shutil.rmtree(folder)
                print(f"Removed {folder} folder")
            except Exception as e:
                print(f"Error removing {folder} folder: {str(e)}")

def main():
    # GitHub repository details
    github_repo_path = r'C:\GitHub\MuleSoft'

    # Initialize repository object
    repo = git.Repo(github_repo_path)
    # Remove untracked files
    for item in repo.untracked_files:
        if os.path.isfile(item) or os.path.isdir(item):
            os.remove(item)
        elif os.path.isdir(item):
            shutil.rmtree(item)

    # Pull changes from remote
    origin = repo.remotes.origin
    origin.pull()

    delete_all_folders(github_repo_path)  
    config_path = r'C:\GitHub\config.json'
    with open(config_path, 'r') as config_file:
        config = json.load(config_file)                
        downloader = AnypointJarDownloader(config['Mule']['Client_id'], config['Mule']['Client_secret'], github_repo_path)
    
    try:
        downloader.authenticate()
        bg_id = downloader.get_business_group_id()
        
        # Get environments first
        environments = downloader.get_environments()
        data = environments['data']
        for env in data:
            if isinstance(env, dict) and 'id' in env and 'name' in env:
                env_id = env['id']
                env_name = env['name']
                print(f"\nProcessing {env_name} (ID: {env_id})...")
                
                apps = downloader.get_applications(bg_id, env_id)
                
                if apps:
                    print(f"Found applications: {[app.get('domain', '') for app in apps]}")
                    for app in apps:
                        if 'domain' in app:
                            downloader.download_jar(app['domain'], env_id, env_name)
                        else:
                            print(f"No domain found for application: {app}")
                    downloader.organize_files(env_name)
                else:
                    print("No applications found in this environment")
            else:
                print(f"Invalid environment data received: {env}")
            
    except Exception as e:
        print(f"Error: {str(e)}")

    # Check if the __pycache__ folder exists and delete it
    pycache_dir = os.path.join(github_repo_path, "__pycache__")
    if os.path.exists(pycache_dir) and os.path.isdir(pycache_dir):
        shutil.rmtree(pycache_dir)
        print(f"Deleted: {pycache_dir}")
    else:
        print(f"__pycache__ folder does not exist at: {pycache_dir}")

    # Set up commit message
    commit_message = 'Automated check in'

    # Set SSH URL for remote origin
    repo.remotes.origin.set_url('git@github.com:theirc-martech-integrations-automations/MuleSoft.git')

    # Check if there are any changes
    if repo.is_dirty(untracked_files=True) or origin.refs[0].commit != repo.head.commit:
        # Add changes and commit
        repo.git.add('--all')
        repo.index.commit(commit_message)

        # Push changes
        origin.push()
        print('Changes committed and pushed successfully.')
    else:
        print('No changes detected.')

if __name__ == "__main__":
    main()