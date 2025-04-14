import os
import subprocess
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Retrieve Supabase connection details
password=os.getenv('password')
user=os.getenv('user')
host=os.getenv('host')
port=os.getenv('port')
dbname=os.getenv('dbname')

SUPABASE_DB_URL = f"postgresql://{user}:{password}@{host}:{port}/{dbname}"

if not SUPABASE_DB_URL:
    raise ValueError("Missing SUPABASE_DB_URL in environment variables.")

# Optionally, set the workdir if your Supabase project directory is not the current directory.
# For example, if your supabase directory is in the root of your project, you can set it to "."
WORKDIR = "."

# Build the command to push your migrations to the Supabase DEV database.
command = [
    "supabase",
    "db",
    "push",
    "--db-url", SUPABASE_DB_URL,
    "--workdir", WORKDIR
]

try:
    # Execute the command using subprocess
    result = subprocess.run(command, input='Y', capture_output=True, text=True, check=True)
    print("Migrations pushed successfully!")
    print(result.stdout)
except subprocess.CalledProcessError as e:
    print("Error running migrations:")
    print(e.stderr)
