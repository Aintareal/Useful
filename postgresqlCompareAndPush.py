import os
import git
from pathlib import Path
import psycopg2
from datetime import datetime
import shutil
import json

# GitHub repository details
github_repo_path = r'C:\GitHub\Postgresql'

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

delete_all_folders(github_repo_path)

def get_connection(dbname, user, password, host, port, sslcert=None, sslkey=None, sslrootcert=None, sslmode='verify-full'):
    """Establish database connection with SSL support"""
    conn_params = {
        "dbname": dbname,
        "user": user,
        "password": password,
        "host": host,
        "port": port
    }
    
    # Add SSL parameters if certificates are provided
    if any([sslcert, sslkey, sslrootcert]):
        conn_params.update({
            "sslmode": sslmode,
            "sslcert": sslcert if sslcert else None,
            "sslkey": sslkey if sslkey else None,
            "sslrootcert": sslrootcert if sslrootcert else None
        })
        # Remove None values
        conn_params = {k: v for k, v in conn_params.items() if v is not None}
    
    return psycopg2.connect(**conn_params)

def get_schemas(cursor):
    """Get all non-system schemas"""
    cursor.execute("""
        SELECT schema_name 
        FROM information_schema.schemata 
        WHERE schema_name NOT IN ('information_schema', 'pg_catalog', 'pg_toast')
        ORDER BY schema_name
    """)
    return [row[0] for row in cursor.fetchall()]

def get_tables_ddl(cursor, schema):
    """Get CREATE TABLE statements"""
    cursor.execute(f"""
        SELECT 
            table_name,
            concat('CREATE TABLE {schema}.', table_name, ' (', chr(10),
                string_agg(
                    concat('    ', column_name, ' ', data_type,
                        CASE 
                            WHEN character_maximum_length IS NOT NULL 
                            THEN concat('(', character_maximum_length, ')')
                            ELSE ''
                        END,
                        CASE WHEN is_nullable = 'NO' THEN ' NOT NULL' ELSE '' END
                    ),
                    ',' || chr(10)
                ),
                chr(10), ');'
            ) as ddl
        FROM information_schema.columns
        WHERE table_schema = %s
        GROUP BY table_schema, table_name
        ORDER BY table_name
    """, (schema,))
    return cursor.fetchall()

def get_functions_ddl(cursor, schema):
    """Get CREATE FUNCTION statements"""
    cursor.execute(f"""
        SELECT 
            proname as function_name,
            pg_get_functiondef(p.oid) as ddl
        FROM pg_proc p
        JOIN pg_namespace n ON p.pronamespace = n.oid
        WHERE n.nspname = %s
        AND p.prokind = 'f'
        ORDER BY proname
    """, (schema,))
    return cursor.fetchall()

def get_procedures_ddl(cursor, schema):
    """Get CREATE PROCEDURE statements"""
    cursor.execute(f"""
        SELECT 
            proname as procedure_name,
            pg_get_functiondef(p.oid) as ddl
        FROM pg_proc p
        JOIN pg_namespace n ON p.pronamespace = n.oid
        WHERE n.nspname = %s
        AND p.prokind = 'p'
        ORDER BY proname
    """, (schema,))
    return cursor.fetchall()

def get_sequences_ddl(cursor, schema):
    """Get CREATE SEQUENCE statements"""
    cursor.execute(f"""
        SELECT 
            sequence_name,
            concat('CREATE SEQUENCE {schema}.', sequence_name, ';') as ddl
        FROM information_schema.sequences
        WHERE sequence_schema = %s
        ORDER BY sequence_name
    """, (schema,))
    return cursor.fetchall()

<<<<<<< HEAD
def write_ddl_files(github_repo_path, schema, obj_type, ddl_list):
    """Write DDL statements to files"""
    schema_dir = Path(github_repo_path) / schema / obj_type
=======
def write_ddl_files(base_dir, schema, obj_type, ddl_list):
    """Write DDL statements to files"""
    schema_dir = Path(base_dir) / schema / obj_type
>>>>>>> 009ff0749271bd11a3ee6a1820f958b6eab2b819
    schema_dir.mkdir(parents=True, exist_ok=True)
    
    for obj_name, ddl in ddl_list:
        file_path = schema_dir / f"{obj_name}.sql"
        with open(file_path, 'w') as f:
            f.write(ddl)

def export_ddls(dbname, user, password, host, port, output_dir, sslcert=None, sslkey=None, sslrootcert=None, sslmode='verify-full'):
    """Main function to export all DDLs"""
    conn = get_connection(dbname, user, password, host, port, sslcert, sslkey, sslrootcert, sslmode)
    cursor = conn.cursor()
    
    schemas = get_schemas(cursor)
    
    for schema in schemas:
        print(f"Processing schema: {schema}")
        
        # Export tables
        tables = get_tables_ddl(cursor, schema)
        write_ddl_files(output_dir, schema, "tables", tables)
        print(f"  Exported {len(tables)} tables")
        
        # Export functions
        functions = get_functions_ddl(cursor, schema)
        write_ddl_files(output_dir, schema, "functions", functions)
        print(f"  Exported {len(functions)} functions")
        
        # Export procedures
        procedures = get_procedures_ddl(cursor, schema)
        write_ddl_files(output_dir, schema, "procedures", procedures)
        print(f"  Exported {len(procedures)} procedures")
        
        # Export sequences
        sequences = get_sequences_ddl(cursor, schema)
        write_ddl_files(output_dir, schema, "sequences", sequences)
        print(f"  Exported {len(sequences)} sequences")
    
    cursor.close()
    conn.close()
def delete_empty_folders(folder_path):
    # Traverse the folder structure from bottom-up
    for root, dirs, files in os.walk(folder_path, topdown=False):
        # Check if the current folder is empty
        if not dirs and not files:
            # Delete the empty folder
            os.rmdir(root)


# Access the database configuration values
# Read the config file
def create_ddls(Env):
    config_path = r'C:\GitHub\config.json'
    with open(config_path, 'r') as config_file:
        config = json.load(config_file)
        DB_PARAMS = {
            "dbname": config[Env]['DB_NAME'],
            "user": config[Env]['DB_USER'],
            "password": config[Env]['DB_PASSWORD'],
            "host": config[Env]['DB_HOST'],
            "port": config[Env]['DB_PORT'],
            "sslmode": "require",
            "sslcert": config[Env]['DB_SSL_CERT'],
            "sslkey": config[Env]['DB_SSL_KEY'],
            "sslrootcert": config[Env]['DB_SSL_ROOT_CERT']}
    # Now db_config contains the connection details
    print(DB_PARAMS)    # Output directory
<<<<<<< HEAD
    OUTPUT_DIR = r'C:\\Github\\Postgresql\\' + Env
=======
    OUTPUT_DIR = Env
>>>>>>> 009ff0749271bd11a3ee6a1820f958b6eab2b819
    # Run the export
    export_ddls(**DB_PARAMS, output_dir=OUTPUT_DIR)
    # Delete empty children folders
    delete_empty_folders(OUTPUT_DIR)

create_ddls('Prod')
create_ddls('Fullmig')

# Check if the __pycache__ folder exists and delete it
base_dir = os.path.dirname(__file__)  # Current script directory
pycache_dir = os.path.join(base_dir, "__pycache__")
if os.path.exists(pycache_dir) and os.path.isdir(pycache_dir):
    shutil.rmtree(pycache_dir)
    print(f"Deleted: {pycache_dir}")
else:
    print(f"__pycache__ folder does not exist at: {pycache_dir}")

# Set up commit message
commit_message = 'Automated check in'

# Set SSH URL for remote origin
repo.remotes.origin.set_url('git@github.com:theirc-martech-integrations-automations/Postgresql.git')

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