import pyodbc
import os
import git
import subprocess
from datetime import datetime
import shutil

# GitHub repository details
github_repo_path = r'C:\Users\kennethn\Documents\GitHub\MSSQL'

#Start with no folders in directory
def delete_all_folders(directory):
    try:
        # Iterate over all entries in the directory
        for entry in os.listdir(directory):
            entry_path = os.path.join(directory, entry)
            # Check if the entry is a directory
            if os.path.isdir(entry_path) and entry != '.git':
                # Recursively remove the directory
                shutil.rmtree(entry_path)
                print(f"Deleted directory: {entry_path}")
        print(f"All folders from '{directory}' have been deleted.")
    except Exception as e:
        print(f"Error deleting folders from '{directory}': {e}")

# Example usage:
delete_all_folders(github_repo_path)

# Directory to store generated scripts
os.makedirs(github_repo_path, exist_ok=True)

# Database connection details
server = '172.24.5.7'
conn_str = f'DRIVER={{SQL Server}};SERVER={server};Trusted_Connection=yes;'

# Connect to the master database to get a list of databases
master_conn_str = conn_str + 'DATABASE=master;'
master_connection = pyodbc.connect(master_conn_str)
master_cursor = master_connection.cursor()

# Query to get a list of user databases
user_db_query = "SELECT name FROM sys.databases WHERE database_id > 4 AND state_desc = 'ONLINE'"
master_cursor.execute(user_db_query)
user_databases = [row[0] for row in master_cursor.fetchall()]

# Iterate through user databases
for database_name in user_databases:
    print(f"Generating scripts for {database_name}...")
    # Connect to the user database
    conn_str_database = conn_str + f'DATABASE={database_name};'
    connection = pyodbc.connect(conn_str_database)
    cursor = connection.cursor()

    # Get tables in the database
    tables_query = "SELECT name FROM sys.tables"
    tables = [row[0] for row in cursor.execute(tables_query)]

    # Get procs in the database
    procedure_query = "SELECT name FROM sys.procedures WHERE type_desc = 'SQL_STORED_PROCEDURE'"
    procedures = [row[0] for row in cursor.execute(procedure_query)]

    # Get views in the database
    views_query = "SELECT name FROM sys.objects WHERE type IN ('V') AND is_ms_shipped = 0"
    views = [row[0] for row in cursor.execute(views_query)]

    # Get UDFs in the database
    udf_query = "SELECT name FROM sys.objects WHERE type IN ('FN') AND is_ms_shipped = 0"
    udfs = [row[0] for row in cursor.execute(udf_query)]

    # Get users in the database
    users_query = "SELECT name FROM sys.database_principals WHERE type_desc = 'SQL_USER'"
    users = [row[0] for row in cursor.execute(users_query)]

    # Create directory for scripts
    script_dir = github_repo_path + "/" + f"{database_name}"
    os.makedirs(script_dir, exist_ok=True)
    os.makedirs(script_dir + '/Tables', exist_ok=True)
    os.makedirs(script_dir + '/Stored Procedures', exist_ok=True)
    os.makedirs(script_dir + '/Views', exist_ok=True)
    os.makedirs(script_dir + '/Users', exist_ok=True)
    os.makedirs(script_dir + '/User Defined Functions', exist_ok=True)

    for table_name in tables:
        # Execute stored procedure for each table
        try:
             # Execute stored procedure
            sp_name = 'sp_GetDDLa'
            cursor.execute(f"EXEC {sp_name} '{table_name}'")

            # Fetch all rows and concatenate into a single string
            result = '\n'.join(row[0] for row in cursor.fetchall())

            # Write to script file
            script_path = os.path.join(script_dir + '/Tables', f'{table_name}.sql')
            with open(script_path, 'w') as script_file:
                script_file.write(f'USE {database_name}\nGO\n\n{result}\n')
        except Exception as e:
            print(f"Error executing stored procedure '{sp_name}' for table '{table_name}': {e}")
    for procedure_name in procedures:
        # Execute stored procedure for each table
        try:
             # Execute stored procedure
            sp_name = 'sp_GetDDLa'
            cursor.execute(f"EXEC {sp_name} '{procedure_name}'")

            # Fetch all rows and concatenate into a single string
            result = '\n'.join(row[0] for row in cursor.fetchall())

            # Write to script file
            script_path = os.path.join(script_dir + '/Stored Procedures', f'{procedure_name}.sql')
            with open(script_path, 'w') as script_file:
                script_file.write(f'USE {database_name}\nGO\n\n{result}\n')
        except Exception as e:
            print(f"Error executing stored procedure '{sp_name}' for proc '{procedure_name}': {e}")

    for view_name in views:
        # Execute stored procedure for each table
        try:
             # Execute stored procedure
            sp_name = 'sp_GetDDLa'
            cursor.execute(f"EXEC {sp_name} '{view_name}'")

            # Fetch all rows and concatenate into a single string
            result = '\n'.join(row[0] for row in cursor.fetchall())

            # Write to script file
            script_path = os.path.join(script_dir + '/Views', f'{view_name}.sql')
            with open(script_path, 'w') as script_file:
                script_file.write(f'USE {database_name}\nGO\n\n{result}\n')
        except Exception as e:
            print(f"Error executing stored procedure '{sp_name}' for proc '{view_name}': {e}")
    for udf_name in udfs:
        # Execute stored procedure for each table
        try:
             # Execute stored procedure
            sp_name = 'sp_GetDDLa'
            cursor.execute(f"EXEC {sp_name} '{udf_name}'")

            # Fetch all rows and concatenate into a single string
            result = '\n'.join(row[0] for row in cursor.fetchall())

            # Write to script file
            script_path = os.path.join(script_dir + '/User Defined Functions', f'{udf_name}.sql')
            with open(script_path, 'w') as script_file:
                script_file.write(f'USE {database_name}\nGO\n\n{result}\n')
        except Exception as e:
            print(f"Error executing stored procedure '{sp_name}' for proc '{udf_name}': {e}")

    for user_name in users:
        # Execute stored procedure for each table
        try:
             # Execute stored procedure
            sp_name = 'sp_GetDDLa'
            cursor.execute(f"EXEC {sp_name} '{user_name}'")

            # Fetch all rows and concatenate into a single string
            result = '\n'.join(row[0] for row in cursor.fetchall())

            # Write to script file
            script_path = os.path.join(script_dir + '/Users', f'{user_name}.sql')
            with open(script_path, 'w') as script_file:
                script_file.write(f'USE {user_name}\nGO\n\n{result}\n')
        except Exception as e:
            print(f"Error executing stored procedure '{sp_name}' for proc '{user_name}': {e}")

    # Close cursor and connection
    cursor.close()
    connection.close()

def delete_empty_folders(folder_path):
    # Traverse the folder structure from bottom-up
    for root, dirs, files in os.walk(folder_path, topdown=False):
        # Check if the current folder is empty
        if not dirs and not files:
            # Delete the empty folder
            os.rmdir(root)

# Delete empty children folders
delete_empty_folders(github_repo_path)

# Set up commit message
commit_message = 'Automated check in'

# Initialize repository object
repo = git.Repo(github_repo_path)

# Set SSH URL for remote origin
repo.remotes.origin.set_url('git@github.com:theirc-martech-integrations-automations/MSSQL.git')

# Pull changes from remote
origin = repo.remotes.origin
origin.pull()

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