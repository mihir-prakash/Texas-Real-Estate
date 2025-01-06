from flask import Flask, request, jsonify, render_template
import requests
from bs4 import BeautifulSoup
import logging
import re
import os

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = Flask(__name__)

def scrape_properties(zip_code, max_budget=None, min_sqft=None, max_sqft=None):
    """
    Scrape real estate properties from HAR.com
    
    Args:
        zip_code (str): ZIP code to search in
        max_budget (int, optional): Maximum price
        min_sqft (int, optional): Minimum square footage
        max_sqft (int, optional): Maximum square footage
    
    Returns:
        list: List of property dictionaries with details
    """
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3"
    }
    
    url = f"https://www.har.com/zipcode_{zip_code}/realestate/for_sale"
    logger.debug(f"Scraping HAR.com with URL: {url}")
    
    try:
        response = requests.get(url, headers=headers)
        if response.status_code != 200:
            logger.error(f"Failed to fetch data from {url}, status code: {response.status_code}")
            return []

        soup = BeautifulSoup(response.content, "html.parser")
        property_elements = soup.find_all("div", class_="cardv2--landscape__content__body")
        
        if not property_elements:
            logger.warning(f"No property elements found for URL: {url}")
            return []

        properties = []
        
        for element in property_elements:
            try:
                # Extract address
                address_element = element.find("div", class_="cardv2--landscape__content__body__details_address_left_add")
                if not address_element:
                    continue
                    
                # Extract price
                price_element = element.find("div", class_="cardv2--landscape__content__body__details_price")
                if not price_element:
                    continue
                price_text = price_element.text.strip()
                price = int(re.sub(r'[^\d]', '', price_text))
                
                # Skip if over budget
                if max_budget and price > max_budget:
                    continue
                
                # Extract image
                image_url = None
                # Try multiple image selectors as HAR.com uses different classes
                image_element = element.find("div", class_="cardv2--landscape__content__body__image__img")
                if not image_element:
                    image_element = element.find("img", class_="property-image")
                
                if image_element:
                    if 'style' in image_element.attrs:
                        style = image_element['style']
                        url_match = re.search(r"url\('([^']+)'\)", style)
                        if url_match:
                            image_url = url_match.group(1)
                    elif 'src' in image_element.attrs:
                        image_url = image_element['src']
                    elif 'data-src' in image_element.attrs:
                        image_url = image_element['data-src']
                
                # Ensure image URL is absolute
                if image_url and not image_url.startswith(('http://', 'https://')):
                    image_url = f"https://www.har.com{image_url}"
                
                # Extract link
                link_element = element.find("a", class_="call_detail3")
                property_url = None
                if link_element and 'href' in link_element.attrs:
                    property_url = "https://www.har.com" + link_element['href']
                
                # Extract features (beds, baths, sqft)
                features = element.find_all("div", class_="cardv2--landscape__content__body__details_features_item")
                beds = baths = sqft = 'N/A'
                
                for feature in features:
                    text = feature.text.strip().lower()
                    if 'bedrooms' in text:
                        beds = feature.find('span').text.strip()
                    elif 'baths' in text:
                        baths = feature.find('span').text.strip()
                    elif 'sqft.' in text:
                        sqft_text = feature.find('span').text.strip()
                        sqft = int(re.sub(r'[^\d]', '', sqft_text))
                        
                        # Skip if outside sqft range
                        if min_sqft and sqft < min_sqft:
                            continue
                        if max_sqft and sqft > max_sqft:
                            continue
                
                property_data = {
                    'address': address_element.text.strip(),
                    'price': f"${price:,}",
                    'beds': str(beds),
                    'baths': str(baths),
                    'sqft': f"{sqft:,} sq.ft." if isinstance(sqft, int) else sqft,
                    'image': image_url or 'https://via.placeholder.com/350x200?text=No+Image',
                    'link': property_url or '#'
                }
                
                properties.append(property_data)
                logger.debug(f"Successfully processed property: {property_data['address']}")
                
            except Exception as e:
                logger.error(f"Error processing property element: {str(e)}")
                continue

        # Sort properties by price (lowest to highest)
        properties.sort(key=lambda x: int(re.sub(r'[^\d]', '', x['price'])))
        return properties[:10]  # Return top 10 properties (now sorted by price)
        
    except Exception as e:
        logger.error(f"Error in scrape_properties: {str(e)}")
        return []

@app.route('/')
def index():
    return render_template('landing.html')

@app.route('/search')
def search_page():
    return render_template('index.html')

@app.route('/search', methods=['POST'])
def search():
    """
    Handle property search requests
    
    Expected JSON payload:
    {
        "zip_code": "77002",
        "max_budget": 500000,  # optional
        "min_sqft": 1000,      # optional
        "max_sqft": 3000       # optional
    }
    """
    try:
        data = request.get_json()
        zip_code = data.get('zip_code')
        max_budget = data.get('max_budget')
        min_sqft = data.get('min_sqft')
        max_sqft = data.get('max_sqft')
        
        logger.debug(f"Search parameters: zip={zip_code}, budget={max_budget}, min_sqft={min_sqft}, max_sqft={max_sqft}")
        
        if not zip_code:
            logger.error("No zip code provided")
            return jsonify([{
                "address": "Please provide a zip code to search.",
                "price": "N/A",
                "beds": "N/A",
                "baths": "N/A",
                "sqft": "N/A",
                "image": "https://via.placeholder.com/350x200?text=No+Zip+Code",
                "link": "#"
            }])
        
        # Convert parameters to integers if provided
        if max_budget:
            max_budget = int(max_budget)
        if min_sqft:
            min_sqft = int(min_sqft)
        if max_sqft:
            max_sqft = int(max_sqft)
            
        properties = scrape_properties(zip_code, max_budget, min_sqft, max_sqft)
        
        if not properties:
            logger.warning("No properties returned from search")
            return jsonify([{
                "address": f"No properties found in {zip_code}. Try a different zip code or adjust your filters.",
                "price": "N/A",
                "beds": "N/A",
                "baths": "N/A",
                "sqft": "N/A",
                "image": "https://via.placeholder.com/350x200?text=No+Properties+Found",
                "link": "#"
            }])
            
        return jsonify(properties)
        
    except Exception as e:
        logger.error(f"Error in search endpoint: {str(e)}")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=3000)
