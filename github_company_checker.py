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
 / ___(_) |_| (_) __| | __| | |  \/  \ \ / /_   _| ____|  |  ___| __ ) 
| |  _| | __| | |/ _` |/ _` | | | | |\/| |\ V /| | | |  _|    | |_  |  _ \ 
| |_| | | |_| | | (_| | (_| | |_| | |  | | | | |_| | |___   |  _| | |_) |
 \____|_|\__|_|_|\__,_|\__,_|\___/|_|  |_| |_|  \__,_|_____|  |_|   |____/ 
                                                                          
"""

# Load environment variables
load_dotenv()

# Load Shodan API keys from .env file
SHODAN_API_KEYS = [os.getenv('SHODAN_API_KEY_1'), os.getenv('SHODAN_API_KEY_2')]

# Set up logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

# Initialize a set to store unique usernames
usernames_set = set()

# Function to search for GitHub profiles
def search_github(company_name):
    try:
        regex = re.sub(r'\s+', '-', company_name.strip().lower())
        search_url = f'https://github.com/{regex}'
        logging.debug(f'Searching GitHub for {company_name} with URL: {search_url}')
        
        response = requests.get(search_url)
        return regex, response.status_code
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
                return result['http']['host'].split('/')[-1]
        return None
    except Exception as e:
        logging.error(f"Error searching Shodan for {company_name}: {e}")
        return None

# Function to process each company name
def process_company(company_name, table):
    github_username, github_status = search_github(company_name)
    shodan_result = search_shodan(company_name)

    if github_status == 200 and github_username not in usernames_set:
        print(Fore.GREEN + f"Found GitHub username for {company_name}: {github_username}")
        usernames_set.add(github_username)
        table.add_row([company_name, github_username, "Found via GitHub"])
    elif shodan_result and shodan_result not in usernames_set:
        print(Fore.CYAN + f"Shodan found a GitHub username for {company_name}: {shodan_result}")
        usernames_set.add(shodan_result)
        table.add_row([company_name, shodan_result, "Found via Shodan"])
    else:
        print(Fore.YELLOW + f"No GitHub username found for {company_name}")
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

    table = PrettyTable(["Company Name", "GitHub Username", "Status"])
    table.align["Company Name"] = "l"
    table.align["GitHub Username"] = "l"
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

    # Save the unique usernames to a file
    with open('github_username.txt', 'w') as f:
        for username in sorted(usernames_set):
            f.write(username + '\n')

    print(table)
    print(Fore.GREEN + "All companies processed.")

if __name__ == '__main__':
    main()
