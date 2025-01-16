import fitz
import os
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


def extract_text_from_pdf(pdf_path):
    text_data = []
    try:
        with fitz.open(pdf_path) as doc:
            for page_num, page in enumerate(doc, start=1):
                text = page.get_text()
                text_data.append({'page': page_num, 'text': text})
    except Exception as e:
        print(f"Error extracting text from PDF: {e}")
    return text_data

def read_text_file(file_path):
    with open(file_path, 'r') as file:
        text_data = file.read()
    return text_data


def extract_folder_content(folder_path):
    folder_data = []
    for root, dirs, files in os.walk(folder_path):
        for file in files:
            file_path = os.path.join(root, file)
            file_extension = os.path.splitext(file)[1].lower()
            
            if file_extension == '.pdf':
                pdf_content = extract_text_from_pdf(file_path)
                folder_data.extend(pdf_content)
            elif file_extension in ['.txt', '.md', '.rst']:
                text_content = read_text_file(file_path)
                relative_path = os.path.relpath(file_path, folder_path)
                folder_data.append({'path': relative_path, 'text': text_content})
    print(folder_data)
    return folder_data






import logging
from urllib.parse import urlparse, urljoin
import requests
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor
from queue import Queue
import time

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def extract_text_from_url(url, max_depth=2, max_pages=100, timeout=500):
    logger.info(f"Starting extraction from URL: {url} with max depth: {max_depth}, max pages: {max_pages}, timeout: {timeout} seconds")
    
    start_time = time.time()
    results = []
    visited_urls = set()
    url_queue = Queue()
    url_queue.put((url, 0))  # (url, depth)

    def crawl_page(url, depth):
        if time.time() - start_time > timeout:
            logger.warning(f"Timeout reached. Stopping crawl for URL: {url}")
            return None
        
        if url in visited_urls:
            logger.debug(f"URL already visited: {url}")
            return None
        
        if len(visited_urls) >= max_pages:
            logger.warning(f"Max pages limit reached. Stopping crawl for URL: {url}")
            return None

        visited_urls.add(url)
        logger.info(f"Crawling page: {url} at depth: {depth}")

        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')

            web_data = {
                'url': url,
                'title': soup.title.string if soup.title else '',
                'sections': []
            }

            current_section = None
            for element in soup.find_all(['h1', 'h2', 'h3', 'p', 'li']):
                if element.name in ['h1', 'h2', 'h3']:
                    if current_section:
                        web_data['sections'].append(current_section)
                    current_section = {
                        'heading': element.get_text(strip=True),
                        'content': []
                    }
                elif element.name in ['p', 'li']:
                    if current_section:
                        current_section['content'].append(element.get_text(strip=True))
                    else:
                        current_section = {
                            'heading': 'Introduction',
                            'content': [element.get_text(strip=True)]
                        }

            if current_section:
                web_data['sections'].append(current_section)

            logger.info(f"Extracted {len(web_data['sections'])} sections from {url}")

            
            if depth < max_depth:
                base_url = urlparse(url)
                for link in soup.find_all('a', href=True):
                    subpage_url = urljoin(url, link['href'])
                    subpage_parsed = urlparse(subpage_url)
                    if subpage_parsed.netloc == base_url.netloc and subpage_url not in visited_urls:
                        logger.debug(f"Adding subpage to queue: {subpage_url}")
                        url_queue.put((subpage_url, depth + 1))

            return web_data

        except requests.RequestException as e:
            logger.error(f"RequestException error extracting text from URL {url}: {e}")
            return {'url': url, 'title': '', 'sections': [], 'error': f"Error fetching URL: {str(e)}"}
        except Exception as e:
            logger.error(f"Unexpected error processing URL {url}: {e}", exc_info=True)
            return {'url': url, 'title': '', 'sections': [], 'error': f"Unexpected error: {str(e)}"}

    with ThreadPoolExecutor(max_workers=5) as executor:
        while not url_queue.empty() and time.time() - start_time < timeout and len(visited_urls) < max_pages:
            current_url, current_depth = url_queue.get()
            future = executor.submit(crawl_page, current_url, current_depth)
            result = future.result()
            if result:
                results.append(result)

    if not results:
        logger.warning("No content extracted")
        return {'url': url, 'title': '', 'sections': [], 'error': "No content extracted"}

    
    combined_result = results[0]
    for result in results[1:]:
        combined_result['sections'].extend(result['sections'])

    logger.info(f"Successfully extracted text from {len(visited_urls)} pages starting from URL: {url}")

    return combined_result


