"""
This script is for scraping Import Industry Advice Notices from the yearly pages, e.g. run it
iian_scraper.py -u https://www.agriculture.gov.au/biosecurity-trade/import/industry-advice/2024
"""

import sys
import re
import argparse
import urllib.request
from pprint import pprint
import requests
from html_table_parser.parser import HTMLTableParser
import pandas as pd
from bs4 import BeautifulSoup
from loguru import logger

logger.remove()
logger.add(sys.stderr, level="INFO")

DAFF = "https://www.agriculture.gov.au/"


def scrape_url(url: str, idx: list[int]=None) -> list[str]:
    """
    Gets the links from the DAFF Import industry advice notices table and fetches their contents
    """
    with urllib.request.urlopen(url) as conn:
        html = conn.read()

    soup = BeautifulSoup(html)
    links = soup.find_all('a')
    lset = set()

    contents = []
    success = False
    for tag in links:
        link = tag.get('href', None)
        if link and link not in lset:
            xxx = re.search("/biosecurity-trade/import/industry-advice/20\d{2}/\d{2,}-\d{4}", link)
            if xxx and len(xxx.group()) >= 54:
                success = True
                # print(link)
                # page = requests.get(f"{DAFF}{link}")
            else:
                xxx = re.search("/import/industry-advice/20\d{2}/\d{2,}", link)
                if xxx and (35 > len(xxx.group()) >= 31):
                    success = True
                    # print(link)
                    # page = requests.get(f"{DAFF}{link}")
                else:
                    xxx = re.search("/node/\d{5}", link)
                    if xxx and (15 > len(xxx.group()) >= 11):
                        success = True
                    else:
                        success = False
                        logger.error(f"\nFailed at the link {link}")
                        continue

        if success:
            logger.info(f"\nReport for the link {link}")
            # Page content from Website URL
            try:
                page = requests.get(f"{DAFF}{link}", timeout=10)
            except requests.exceptions.Timeout:
                logger.error("Timed out")
            else:
                text = remove_tags(page.content)
                try:
                    logger.info(f"\n{text}")
                except UnicodeEncodeError as _e:
                    logger.exception(f"\nSomething wrong: {_e}")
                finally:
                    contents.append(text)
                    success = False
        lset.add(link)

    if idx:
        logger.info(f"\nMust drop these indices: {idx}")
        for _i in idx:
            tmp = contents.pop(_i)
            logger.info(f"\nDropping {_i}: {tmp}")

    return contents


def remove_tags(html) -> str:
    """
    Function to remove tags from a html document
    """
    # parse html content
    soup = BeautifulSoup(html, "html.parser")
    for data in soup(['style', 'script']):
        # Remove tags
        data.decompose()
    # return data by retrieving the tag content
    return ' '.join(soup.stripped_strings)


def url_get_contents(url: str) -> bytes:
    """
    Opens a website and read its
    binary contents (HTTP Response Body)
    """
    # making request to the website
    req = urllib.request.Request(url=url)
    with urllib.request.urlopen(req) as _f:
        dhtml = _f.read()

    #reading contents of the website
    return dhtml


def main(url: str, nmbrs: list[str]=None) -> None:
    """
    Gets the content of the URL link which has the table with notices for a given year.
    The table column 'Numbers' is used to filter out the rows without links (likely expired),
    one passes these with the option -n and here they are optionally provided in the
    argument nmbrs.
    """
    # defining the html contents of a URL.
    xhtml = url_get_contents(url).decode('utf-8')

    # Defining the HTMLTableParser object
    parser = HTMLTableParser()

    # feeding the html contents in the
    # HTMLTableParser object
    parser.feed(xhtml)

    # Now finally obtaining the data of
    # the table required
    try:
        pprint(parser.tables[0])
    except UnicodeEncodeError as _e:
        logger.exception(f"\nCan't print the table: {_e}")

    # converting the parsed data to dataframe
    parser.tables[0].pop(0)
    logger.info("\n\nPANDAS DATAFRAME\n")
    _df = pd.DataFrame(parser.tables[0], columns=['Date', 'Number', 'Description'])
    idx = _df.index[_df['Description'].str.contains("Please refer to IAN")].to_list()
    idx.reverse()
    if nmbrs:
        damask = _df['Number'].isin(nmbrs)
        _df.drop(damask.index[damask], axis=0, inplace=True)

    _df['full_text'] = scrape_url(url, idx)
    try:
        logger.info(f"\n{_df}")
    except UnicodeEncodeError as _e:
        logger.exception(f"\nCan't print the dataframe: {_e}")
    finally:
        csv_file = input("CSV file name? ")
        _df.to_csv(csv_file, index=False)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", "-u", required=True, help="The URL to scrape the table and links")
    ap.add_argument("--nr_list", "-n", required=False, nargs="+",
            help="The 'Number' values without url links, e.g. -n 154-2018 86-2018 36-2018")
    ARG = vars(ap.parse_args())
    if "nr_list" in ARG:
        main(ARG["url"], ARG["nr_list"])
    else:
        main(ARG["url"])
