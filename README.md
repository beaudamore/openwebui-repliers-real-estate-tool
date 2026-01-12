# OpenWebUI Repliers Real Estate Tool

Real estate listing search tool for OpenWebUI powered by the Repliers API, providing comprehensive property search with detailed filters and formatted results.

**Version:** 1.0.0  
**Author:** Beau D'Amore ([www.damore.ai](https://www.damore.ai))

## Features

- **Comprehensive Property Search**:
  - Search by city, state, county, or ZIP code
  - Property type filtering (house, condo, townhouse, multi-family, land, etc.)
  - Price range and bedroom/bathroom filters
  - Square footage and lot size criteria
  - Year built and property status filters

- **Rich Listing Data**:
  - Complete property details (beds, baths, sqft, lot size)
  - Full address information
  - Pricing and tax information
  - Property features and amenities
  - HOA information
  - Days on market
  - Direct listing URLs

- **Smart Location Parsing**:
  - Automatic "City, State" splitting
  - Support for multiple location formats
  - Flexible location search

- **Formatted Results**:
  - Clean, organized listing summaries
  - Property highlights
  - Easy-to-read formatting
  - Image placeholders for integration

- **Flexible API Integration**:
  - Configurable API endpoint
  - Custom header support
  - Timeout and error handling

## Installation

### Requirements

```bash
pip install requests pydantic
```

### Setup in OpenWebUI

1. Upload `tools/repliers_search_tool_v2.py` to OpenWebUI
2. Configure valves:
   - Set Repliers API base URL
   - Add API key (if required)
   - Adjust default search parameters

## Usage

### Search Examples

```
"Find houses for sale in Miami, FL under $500k"
"Search for 3 bedroom condos in downtown Chicago"
"Show me waterfront properties in Seattle"
"Find land for sale in Austin, Texas"
"Search for townhouses with pool in San Diego"
```

### Key Features

- **Property Types**: House, Condo, Townhouse, Multi-Family, Land, Commercial, Mobile/Manufactured
- **Status Filters**: Active, Pending, Sold, Off Market
- **Price Ranges**: Minimum and maximum price filtering
- **Size Criteria**: Bedrooms, bathrooms, square footage, lot size
- **Amenities**: Pool, waterfront, garage, and more

## Configuration (Valves)

### API Settings

- **api_base_url**: Repliers API endpoint
- **api_key**: Authentication key (if required)
- **timeout**: Request timeout in seconds (default: 30)

### Search Defaults

- **default_limit**: Maximum results per search (default: 20)
- **default_property_type**: Default property type filter
- **enable_debug**: Show search parameters in output

See the tool's valve configuration for all available options.

## API Integration

This tool integrates with the Repliers real estate API. For API documentation and access:
- Contact Repliers for API credentials
- Review `repliersapi.txt` for API details
- See `json/` folder for example response formats

## Sample Data

The repository includes:
- Example JSON responses (`json/repliers-api-json-listing-result-example*.json`)
- N8N workflow examples (`n8n/`)
- Postman collection for testing (`postman/`)
- System prompts for real estate assistants (`prompts/`)

## Documentation

- API Documentation: See `repliersapi.txt`
- Example Responses: See `json/` directory
- System Prompts: See `prompts/` directory

## License

MIT License - See individual repository for details

## Author

**Beau D'Amore**  
[www.damore.ai](https://www.damore.ai)
