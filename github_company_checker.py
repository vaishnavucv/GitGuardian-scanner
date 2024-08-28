import requests
import re
import logging
import threading
from dotenv import load_dotenv
import os
import random
import colorama
from colorama import Fore, Style
from shodan import Shodan
import sys
import argparse
from prettytable import PrettyTable

colorama.init(autoreset=True)

# ASCII Art Banner
BANNER = r"""
  ____ _ _   _ _     _     _   _ ____  _____  __     _______    _____ ____  
 / ___(_) |_| (_) __| | __| | | | |  \/  \ \ / /_   _| ____|  |  ___| __ ) 
| |  _| | __| | |/ _` |/ _` | | | | |\/| |\ V /| | | |  _|    | |_  |  _ \ 
| |_| | | |_| | | (_| | (_| | |_| | |  | | | | | |_| | |___   |  _| | |_) |
 \____|_|\__|_|_|\__,_|\__,_|\___/|_|  |_| |_|  \__,_|_____|  |_|   |____/ 
                                                                          
"""

# Load environment variables
load_dotenv()

# Load Shodan API keys from .env file
SHODAN_API_KEYS = [os.getenv('SHODAN_API_KEY_1'), os.getenv('SHODAN_API_KEY_2')]

# Set up logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

# Function to search for GitHub profiles
def search_github(company_name):
    try:
        regex = re.sub(r'\s+', '-', company_name.strip().lower())
        search_url = f'https://github.com/{regex}'
        logging.debug(f'Searching GitHub for {company_name} with URL: {search_url}')
        
        response = requests.get(search_url)
        return search_url, response.status_code
    except Exception as e:
        logging.error(f"Error searching GitHub for {company_name}: {e}")
        return None, None

# Function to search Shodan
def search_shodan(company_name):
    try:
        api_key = random.choice(SHODAN_API_KEYS)
        shodan_api = Shodan(api_key)
        results = shodan_api.search(company_name)
        for result in results['matches']:
            if 'github.com' in result.get('http', {}).get('host', ''):
                return result['http']['host']
        return None
    except Exception as e:
        logging.error(f"Error searching Shodan for {company_name}: {e}")
        return None

# Function to process each company name
def process_company(company_name, table):
    github_url, github_status = search_github(company_name)
    shodan_result = search_shodan(company_name)

    if github_status == 200:
        print(Fore.GREEN + f"Found GitHub profile for {company_name}: {github_url}")
        with open('github_profiles.txt', 'a') as f:
            f.write(github_url + '\n')
        table.add_row([company_name, github_url, "Found via GitHub"])
    elif shodan_result:
        print(Fore.CYAN + f"Shodan found a GitHub link for {company_name}: {shodan_result}")
        with open('github_profiles.txt', 'a') as f:
            f.write(f"https://{shodan_result}" + '\n')
        table.add_row([company_name, f"https://{shodan_result}", "Found via Shodan"])
    else:
        print(Fore.YELLOW + f"No GitHub profile found for {company_name}")
        table.add_row([company_name, "N/A", "Not Found"])

# Main function
def main():
    parser = argparse.ArgumentParser(description="GitHub Company Profile Checker")
    parser.add_argument('-w', '--file', type=str, help='Specify the .txt file containing the company names', required=True)
    
    # Display help if no arguments are provided
    if len(sys.argv) == 1:
        parser.print_help(sys.stderr)
        sys.exit(1)

    args = parser.parse_args()

    print(BANNER)

    # Load company names from the provided file
    try:
        with open(args.file, 'r') as file:
            companies = file.readlines()
    except FileNotFoundError:
        print(Fore.RED + f"File '{args.file}' not found.")
        sys.exit(1)

    table = PrettyTable(["Company Name", "GitHub Profile", "Status"])
    table.align["Company Name"] = "l"
    table.align["GitHub Profile"] = "l"
    table.align["Status"] = "l"

    # Process each company name in a separate thread
    threads = []
    for company in companies:
        t = threading.Thread(target=process_company, args=(company.strip(), table))
        t.start()
        threads.append(t)

    # Wait for all threads to finish
    for t in threads:
        t.join()

    print(table)
    print(Fore.GREEN + "All companies processed.")

if __name__ == '__main__':
    main()
