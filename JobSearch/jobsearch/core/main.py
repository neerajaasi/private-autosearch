import shutil
import subprocess
from pathlib import Path
from datetime import datetime
import argparse
import yaml

# ------------------------------------------------------
# PATHS
# ------------------------------------------------------
BASE_PATH = Path("/Users/N/git/private-autosearch/JobSearch/jobsearch")

TEMPLATES_PATH = BASE_PATH / "Templates"
CONFIG_PATH = BASE_PATH / "config"
CORE_PATH = BASE_PATH / "core"

GOOGLE_DRIVE_BASE_Flinks = Path(
    "/Users/N/Library/CloudStorage/GoogleDrive-neerajaasi@aaratechinc.com/My Drive/Links-Female"
)
GOOGLE_DRIVE_BASE_LinkedInAll = Path(
    "/Users/N/Library/CloudStorage/GoogleDrive-neerajaasi@aaratechinc.com/My Drive/Links-LinkedInAll"
)
GOOGLE_DRIVE_BASE_LinkedInGuidewire = Path(
    "/Users/N/Library/CloudStorage/GoogleDrive-neerajaasi@aaratechinc.com/My Drive/Links-LinkedInGuidewire"
)
GOOGLE_DRIVE_BASE_LinkedInFemale = Path(
    "/Users/N/Library/CloudStorage/GoogleDrive-neerajaasi@aaratechinc.com/My Drive/Links-LinkedInFemale"
)
GOOGLE_DRIVE_BASE_LinkedInPran = Path(
    "/Users/N/Library/CloudStorage/GoogleDrive-neerajaasi@aaratechinc.com/My Drive/Links-PR"
)

today = datetime.now().strftime("%Y-%m-%d")

# ------------------------------------------------------
# ARGUMENTS
# ------------------------------------------------------
parser = argparse.ArgumentParser()
parser.add_argument("--gender", choices=["male", "female", "pran", "all"], required=True)
args = parser.parse_args()
gender = args.gender

# ------------------------------------------------------
# HELPERS
# ------------------------------------------------------
def copy_config(template_name: str, target_name: str):
    source = TEMPLATES_PATH / template_name
    destination = CONFIG_PATH / target_name

    if not source.exists():
        print(f"[ERROR] Template not found: {source}")
        return False

    shutil.copy(source, destination)
    print(f"[INFO] Copied {template_name} → {target_name}")
    return True


def run_script(script_name: str):
    script_path = CORE_PATH / script_name

    if not script_path.exists():
        print(f"[ERROR] Script not found: {script_path}")
        return False

    print(f"[INFO] Running {script_path} ...")
    subprocess.run(["python", str(script_path)], check=True)
    return True


def create_date_folder(base_path: Path):
    today_folder = datetime.now().strftime("%Y-%m-%d")
    dated_path = base_path / today_folder
    dated_path.mkdir(parents=True, exist_ok=True)
    print(f"[INFO] Using Drive folder: {dated_path}")
    return dated_path


def get_latest_file(folder_path: Path, prefix="LinkedIn_Jobs_", ext=".xlsx"):
    files = list(folder_path.glob(f"{prefix}*{ext}"))

    if not files:
        return None

    latest_file = max(files, key=lambda f: f.stat().st_mtime)
    print(f"[INFO] Latest file selected: {latest_file}")
    return latest_file


# ------------------------------------------------------
# EXECUTION BLOCK
# ------------------------------------------------------
def run_linkedin_flow(template_name, drive_path):
    if copy_config(template_name, "linkedinconfig.yaml"):
        if run_script("linkedin.py"):

            # Read output folder from config
            config_file = CONFIG_PATH / "linkedinconfig.yaml"

            with open(config_file, "r") as f:
                cfg = yaml.safe_load(f)

            output_root = cfg.get("output_root", "results/linkedin")
            source_folder = BASE_PATH / output_root

            source_file = get_latest_file(source_folder)
            dated_path = create_date_folder(drive_path)

            if source_file and source_file.exists():
                shutil.copy2(source_file, dated_path / source_file.name)
                print(f"[INFO] Copied → {dated_path}")
            else:
                print(f"[WARN] No file found in {source_folder}")


def run_dice_flow(dated_path):
    if copy_config("diceconfig.yaml", "diceconfig.yaml"):
        if run_script("dice_links.py"):

            source_folder = BASE_PATH / "results" / "dice"
            source_file = get_latest_file(source_folder, prefix="dice_jobs_listitems_")

            #dated_path = create_date_folder(GOOGLE_DRIVE_BASE_Flinks)

            if source_file and source_file.exists():
                shutil.copy2(source_file, GOOGLE_DRIVE_BASE_LinkedInFemale, dated_path / source_file.name)
                print(f"[INFO] Copied Dice → {GOOGLE_DRIVE_BASE_LinkedInFemale}")
            else:
                print(f"[WARN] No Dice file found")


# ------------------------------------------------------
# MAIN
# ------------------------------------------------------
def main():

    # ---------------- MALE ----------------
    if gender in ["male", "all"]:
        print("\n===== RUNNING MALE FLOWS =====")
        run_linkedin_flow("linkedinconfig-all.yaml", GOOGLE_DRIVE_BASE_LinkedInAll)
        run_linkedin_flow("linkedinconfig-guidewire.yaml", GOOGLE_DRIVE_BASE_LinkedInGuidewire)

    # ---------------- FEMALE ----------------
    if gender in ["female", "all"]:
        print("\n===== RUNNING FEMALE FLOWS =====")

        source_folder = BASE_PATH / "results" / "linkedin"
        source_file = get_latest_file(source_folder)

        ''' fallback if not exists
        if not source_file:
            print("[INFO] LinkedIn-All not found. Running it once...")
            run_linkedin_flow("linkedinconfig-all.yaml", GOOGLE_DRIVE_BASE_LinkedInAll)
            source_file = get_latest_file(source_folder)
        '''
        dated_path = create_date_folder(GOOGLE_DRIVE_BASE_LinkedInFemale)

        if source_file and source_file.exists():
            shutil.copy2(source_file, dated_path / source_file.name)
            print(f"[INFO] Copied LinkedIn-All → Female folder")
        else:
            print(f"[WARN] No LinkedIn-All file found")

        run_dice_flow(dated_path)

    # ---------------- PRAN ----------------
    if gender in ["pran","all"]:
        print("\n===== RUNNING PRAN FLOWS =====")


        if run_script("linkedin_cad.py"):
    #run_linkedin_flow("linkedinconfig-pran.yaml", GOOGLE_DRIVE_BASE_LinkedInPran)
            config_file = CONFIG_PATH / "linkedinconfig-cad.yaml"
            with open(config_file, "r") as f:
                cfg = yaml.safe_load(f)
            output_root = cfg.get("output_root", "results/linkedin-Pran")
            source_folder = BASE_PATH / output_root

            source_file = get_latest_file(source_folder)
            dated_path = create_date_folder(GOOGLE_DRIVE_BASE_LinkedInPran)

            if source_file and source_file.exists():
                shutil.copy2(source_file, dated_path / source_file.name)
                print(f"[INFO] Copied → {dated_path}")
            else:
                print(f"[WARN] No file found in {source_folder}")

# ------------------------------------------------------
# ENTRY POINT
# ------------------------------------------------------
if __name__ == "__main__":
    main()